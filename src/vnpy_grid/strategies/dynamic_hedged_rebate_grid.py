from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set
from datetime import datetime

from vnpy_ctastrategy import (
    CtaTemplate,
    TickData,
    BarData,
    ArrayManager,
)
from vnpy.trader.constant import Direction, Offset
from vnpy.trader.object import OrderData, TradeData


@dataclass
class LegRecord:
    direction: Direction
    entry_price: float
    volume: float
    vt_orderids: List[str]
    open_dt: datetime | None = None
    open_fee_quote: float = 0.0
    open_is_maker: bool = True


class DynamicHedgedRebateGridStrategy(CtaTemplate):
    """
    动态对冲返佣网格（回测实现）。
    - 在基准价两侧按固定间距布网格，多空对称挂单；
    - 任一腿开仓后即刻挂对称止盈；
    - 止盈利润（含手续费/返佣）复利到对应方向手数；
    - 达到最大回撤阈值时暂停交易并撤单。
    """

    author = "Augment"

    # 可调参数
    parameters = [
        "grid_pct",
        "levels",
        "long_size_init",
        "short_size_init",
        "min_order_size",
        "max_individual_position_size",
        "max_net_exposure_limit",
        "max_account_drawdown_percent",
        # 费用/返佣模型
        "maker_rebate_rate",
        "taker_fee_rate",
        "assume_maker_for_resting_orders",
        # 初始资金（用于回撤监控，单位：USDT）
        "initial_equity_quote",
        # 价格舍入（避免浮点误差导致价位键不一致）
        "price_round_dp",
        # 仅做被动挂单模式（多头只挂在基准价下方，空头只挂在基准价上方）
        "maker_only_mode",
    ]

    # 可观察变量
    variables = [
        "base_price",
        "long_size",
        "short_size",
        "rebate_eth_long",
        "rebate_eth_short",
        # 统计
        "realized_pnl_quote",
        "fee_rebate_quote",
        "fee_paid_quote",
        "maker_fills",
        "taker_fills",
        "equity_quote",
        "max_drawdown_percent_achieved",
    ]

    # 参数默认值
    grid_pct: float = 0.0016  # 0.16%
    levels: int = 5
    long_size_init: float = 0.005
    short_size_init: float = 0.005
    min_order_size: float = 0.005
    max_individual_position_size: float = 1.0
    max_net_exposure_limit: float = 5.0
    max_account_drawdown_percent: float = 0.5

    # 费用/返佣（按名义价值比例；Maker 返佣为负，Taker 手续费为正）
    maker_rebate_rate: float = 0.00005
    taker_fee_rate: float = 0.0007
    assume_maker_for_resting_orders: bool = True

    # 资金与风控
    initial_equity_quote: float = 10_000.0

    # 价格小数位舍入（避免浮点误差）
    price_round_dp: int = 2
    maker_only_mode: bool = True

    # 运行时变量
    base_price: float = 0.0
    long_size: float = 0.0
    short_size: float = 0.0
    rebate_eth_long: float = 0.0
    rebate_eth_short: float = 0.0

    realized_pnl_quote: float = 0.0
    fee_rebate_quote: float = 0.0
    fee_paid_quote: float = 0.0
    maker_fills: int = 0
    taker_fills: int = 0
    equity_quote: float = 0.0
    max_drawdown_percent_achieved: float = 0.0

    am: ArrayManager

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()

        # 订单簿：价格 -> 订单id 列表
        self.open_long_orders: Dict[float, List[str]] = {}
        self.open_short_orders: Dict[float, List[str]] = {}

        # 当前活跃网格价集合（增量平移）
        self.active_grid_prices: Set[float] = set()

        # 止盈订单：vt_orderid -> LegRecord
        self.take_profit_orders: Dict[str, LegRecord] = {}

        self.inited_price_ready = False
        self.paused_by_drawdown = False
        self.equity_quote = self.initial_equity_quote

    def on_init(self):
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")
        self.put_event()

    def on_stop(self):
        self.write_log("策略停止")

    def _sync_cn_aliases(self) -> None:
        # 仅用于GUI显示（可选）
        self.基准价 = self.base_price
        self.网格间距 = self.grid_pct
        self.网格层数 = self.levels
        self.多头规模 = self.long_size
        self.空头规模 = self.short_size
        self.权益USDT = self.equity_quote
        self.回撤最大百分比 = self.max_drawdown_percent_achieved

    def on_tick(self, tick: TickData):
        # Tick 模式下，首个 tick 铺网格
        if not self.inited_price_ready:
            if not self.trading or self.paused_by_drawdown:
                return
            price = tick.last_price or tick.ask_price_1 or tick.bid_price_1
            if not price:
                return
            self.base_price = float(price)
            self.long_size = max(self.long_size_init, self.min_order_size)
            self.short_size = max(self.short_size_init, self.min_order_size)
            self._rebuild_grid(self.base_price)
            self.inited_price_ready = True
            self._sync_cn_aliases()
            self.put_event()

    def on_bar(self, bar: BarData):
        # Bar 模式下，首根K线铺网格
        if not self.inited_price_ready:
            if not self.trading or self.paused_by_drawdown:
                return
            self.base_price = bar.close_price
            self.long_size = max(self.long_size_init, self.min_order_size)
            self.short_size = max(self.short_size_init, self.min_order_size)
            self._rebuild_grid(bar.close_price)
            self.inited_price_ready = True
            self._sync_cn_aliases()
            self.put_event()
            return

        self.put_event()

    def on_order(self, _order: OrderData):
        return

    def _calc_fee(self, price: float, volume: float, is_maker: bool) -> float:
        """计算一笔成交的费用（正=付费，负=返佣），并更新统计。"""
        notion = abs(price) * abs(volume)
        fee = (-self.maker_rebate_rate if is_maker else self.taker_fee_rate) * notion
        if is_maker:
            self.fee_rebate_quote += -fee
            self.maker_fills += 1
        else:
            self.fee_paid_quote += fee
            self.taker_fills += 1
        return fee

    # 工具：价格舍入与网格计算
    def _round_price(self, p: float) -> float:
        try:
            dp = int(self.price_round_dp)
        except Exception:
            dp = 2
        return round(p, dp) if dp >= 0 else p

    def _compute_grid_prices(self) -> List[float]:
        ps: List[float] = []
        for i in range(1, self.levels + 1):
            ps.append(self._round_price(self.base_price * (1.0 - self.grid_pct * i)))
            ps.append(self._round_price(self.base_price * (1.0 + self.grid_pct * i)))
        return sorted(set(ps))

    def _check_drawdown_and_pause(self):
        if self.initial_equity_quote <= 0:
            return
        dd = max(0.0, (self.initial_equity_quote - self.equity_quote) / self.initial_equity_quote)
        self.max_drawdown_percent_achieved = max(self.max_drawdown_percent_achieved, dd)
        if dd >= self.max_account_drawdown_percent and not self.paused_by_drawdown:
            self.paused_by_drawdown = True
            self.cancel_all()
            self.write_log(f"达到回撤阈值，暂停交易：dd={dd:.2%}")

    def on_trade(self, trade: TradeData):
        price = trade.price
        vol = trade.volume
        dir_ = trade.direction
        off = trade.offset

        # 开仓后：下止盈；记录开仓费用
        if off == Offset.OPEN:
            is_maker_open = bool(self.assume_maker_for_resting_orders)
            open_fee = self._calc_fee(price, vol, is_maker_open)

            if dir_ == Direction.LONG:
                tp_price = price * (1.0 + self.grid_pct)
                vtids = self.sell(tp_price, vol)  # 平多
            else:
                tp_price = price * (1.0 - self.grid_pct)
                vtids = self.cover(tp_price, vol)  # 平空

            vtid = vtids[0] if vtids else ""
            if vtid:
                self.take_profit_orders[vtid] = LegRecord(
                    direction=dir_,
                    entry_price=price,
                    volume=vol,
                    vt_orderids=[trade.vt_orderid],
                    open_dt=getattr(trade, "datetime", None),
                    open_fee_quote=open_fee,
                    open_is_maker=is_maker_open,
                )

            # 成交后更新基准价并平移网格
            self.base_price = price
            if not self.paused_by_drawdown:
                self._rebuild_grid(price)
            self._sync_cn_aliases()
            self.put_event()
            return

        # 止盈平仓：按净收益（含费）复利 size
        if off == Offset.CLOSE and trade.vt_orderid in self.take_profit_orders:
            rec = self.take_profit_orders.pop(trade.vt_orderid)
            is_maker_close = bool(self.assume_maker_for_resting_orders)
            close_fee = self._calc_fee(trade.price, rec.volume, is_maker_close)

            if rec.direction == Direction.LONG:
                gross_quote = max(0.0, trade.price - rec.entry_price) * rec.volume
            else:
                gross_quote = max(0.0, rec.entry_price - trade.price) * rec.volume

            net_quote = gross_quote - (rec.open_fee_quote + close_fee)
            self.realized_pnl_quote += net_quote
            self.equity_quote = self.initial_equity_quote + self.realized_pnl_quote

            eth_gain = net_quote / max(trade.price, 1e-9)
            if rec.direction == Direction.LONG:
                self.rebate_eth_long += max(0.0, eth_gain)
                self.long_size = min(max(self.long_size + eth_gain, self.min_order_size), self.max_individual_position_size)
            else:
                self.rebate_eth_short += max(0.0, eth_gain)
                self.short_size = min(max(self.short_size + eth_gain, self.min_order_size), self.max_individual_position_size)

            # 净敞口风控（简单手数限制）
            net_pos = self.pos
            if abs(net_pos) > self.max_net_exposure_limit:
                reduce_qty = min(abs(net_pos), (self.long_size if net_pos > 0 else self.short_size))
                if net_pos > 0:
                    self.sell(trade.price * (1 + self.grid_pct * 0.5), reduce_qty)
                elif net_pos < 0:
                    self.cover(trade.price * (1 - self.grid_pct * 0.5), reduce_qty)

            self._check_drawdown_and_pause()
            self.put_event()

    def _rebuild_grid(self, _unused_ref_price: float) -> None:
        """增量网格平移：首次全量挂单；其后仅撤远端一排、补另一端一排。"""
        if self.paused_by_drawdown:
            return

        new_prices = self._compute_grid_prices()
        new_set = set(new_prices)

        # 首次：无活跃集合 -> 全量挂单
        if not self.active_grid_prices:
            self._cancel_all_grid_orders()
            for p in new_prices:
                self._place_grid_pair(p)
            self.active_grid_prices = new_set
        else:
            old_set = set(self.active_grid_prices)
            to_cancel = sorted(old_set - new_set)
            to_place = sorted(new_set - old_set)
            for p in to_cancel:
                self._cancel_price_orders(p)
            for p in to_place:
                self._place_grid_pair(p)
            self.active_grid_prices = new_set

    # ——— 网格下单/撤单子函数 ———
    def _place_grid_pair(self, price: float) -> None:
        price = self._round_price(price)
        long_qty = max(self.min_order_size, min(self.long_size, self.max_individual_position_size))
        short_qty = max(self.min_order_size, min(self.short_size, self.max_individual_position_size))

        vtids_long: List[str] = []
        vtids_short: List[str] = []

        # maker_only_mode：仅做被动挂单（以基准价近似判断）
        if (not self.maker_only_mode) or (price < self.base_price):
            if long_qty > 0:
                vtids_long = self.buy(price, long_qty)
        if (not self.maker_only_mode) or (price > self.base_price):
            if short_qty > 0:
                vtids_short = self.short(price, short_qty)

        if vtids_long:
            self.open_long_orders[price] = vtids_long
        if vtids_short:
            self.open_short_orders[price] = vtids_short

    def _cancel_price_orders(self, price: float) -> None:
        price = self._round_price(price)
        ids_long = self.open_long_orders.pop(price, [])
        ids_short = self.open_short_orders.pop(price, [])
        for vt in ids_long + ids_short:
            self.cancel_order(vt)

    def _cancel_all_grid_orders(self) -> None:
        for ids in list(self.open_long_orders.values()):
            for vt in ids:
                self.cancel_order(vt)
        for ids in list(self.open_short_orders.values()):
            for vt in ids:
                self.cancel_order(vt)
        self.open_long_orders.clear()
        self.open_short_orders.clear()

    def on_stop_order(self, _stop_order):
        return
