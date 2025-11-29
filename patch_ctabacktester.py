#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VN.PY CTA 鍥炴祴寮曟搸闈炰镜鍏ュ紡琛ヤ竵

鍔熻兘锛?
1. 淇绛栫暐鍔犺浇闂锛堟樉绀哄紓甯镐俊鎭€屼笉鏄潤榛樺拷鐣ワ級
2. 娴佸紡鍥炴祴锛堥伩鍏嶄竴娆℃€у姞杞藉叏閲忔暟鎹級
3. 鍐呭瓨浼樺寲缁熻寮€鍏筹紙鍙€夋嫨涓嶄繚瀛樺畬鏁?TradeData 鍒楄〃锛?
4. GUI 澶嶉€夋鏀寔
5. 鍥捐〃鏁板瓧鏍煎紡鍖栦紭鍖?

浣跨敤鏂规硶锛?
鍦?VN Trader 鍚姩鍓嶅鍏ユ妯″潡鍗冲彲鑷姩搴旂敤琛ヤ竵
"""

import traceback
import importlib
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine, Event
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import BaseDatabase, get_database
from vnpy.trader.utility import extract_vt_symbol
from vnpy_ctastrategy.template import CtaTemplate, TargetPosTemplate
from vnpy_ctastrategy.backtesting import BacktestingEngine, DailyResult
from vnpy_ctabacktester.engine import BacktesterEngine, EVENT_BACKTESTER_BACKTESTING_FINISHED
from vnpy_ctabacktester.locale import _


def patched_load_strategy_class(self) -> None:
    """
    修复版本的策略类加载方法，支持多个可能的策略目录
    """
    import vnpy_ctastrategy

    # 加载内置策略
    app_path: Path = Path(vnpy_ctastrategy.__file__).parent
    path1: Path = app_path.joinpath("strategies")
    self.load_strategy_class_from_folder(path1, "vnpy_ctastrategy.strategies")

    # 本地策略目录（优先新路径，其次旧路径，依次尝试）
    roots = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parents[1],
    ]
    candidates: list[tuple[Path, str]] = []
    for r in roots:
        candidates.extend([
            (r / 'src' / 'vnpy_grid' / 'strategies', 'vnpy_grid.strategies'),
            (r / 'strategies', 'strategies'),
        ])

    for path2, modname in candidates:
        if path2.exists():
            print(f"Found local strategy dir: {path2}")
            self.load_strategy_class_from_folder(path2, modname)
            break
    else:
        print("No local strategy directory found")

def patched_load_strategy_class_from_folder(self, path: Path, module_name: str = "") -> None:
    """
    淇鐗堟湰鐨勭瓥鐣ユ枃浠跺す鍔犺浇鏂规硶锛屾樉绀鸿缁嗚皟璇曚俊鎭?
    """
    print(f"馃攳 鎵弿绛栫暐鐩綍: {path} (瀛樺湪: {path.exists()})")

    if not path.exists():
        print(f"鈿狅笍 鐩綍涓嶅瓨鍦紝璺宠繃: {path}")
        return

    from glob import glob

    for suffix in ["py", "pyd", "so"]:
        pathname: str = str(path.joinpath(f"*.{suffix}"))
        print(f"馃攳 鎼滅储妯″紡: {pathname}")

        for filepath in glob(pathname):
            filename: str = Path(filepath).stem
            name: str = f"{module_name}.{filename}"
            print(f"馃搧 鍙戠幇鏂囦欢: {filepath} -> 妯″潡鍚? {name}")
            self.load_strategy_class_from_module(name)

def patched_load_strategy_class_from_module(self, module_name: str) -> None:
    """
    淇鐗堟湰鐨勭瓥鐣ユā鍧楀姞杞芥柟娉曪紝鏄剧ず璇︾粏寮傚父淇℃伅
    """
    print(f"馃摝 灏濊瘯鍔犺浇妯″潡: {module_name}")
    try:
        module = importlib.import_module(module_name)
        # 閲嶈浇妯″潡锛岀‘淇濆鏋滅瓥鐣ユ枃浠朵腑鏈変换浣曚慨鏀癸紝鑳藉绔嬪嵆鐢熸晥銆?
        importlib.reload(module)

        for name in dir(module):
            value = getattr(module, name)
            if (
                isinstance(value, type)
                and issubclass(value, CtaTemplate)
                and value not in {CtaTemplate, TargetPosTemplate}
            ):
                self.classes[value.__name__] = value
                # 娣诲姞璋冭瘯淇℃伅
                print(f"鉁?鍔犺浇绛栫暐绫? {value.__name__} from {module_name}")
    except Exception as e:
        # 鏄剧ず璇︾粏寮傚父淇℃伅鑰屼笉鏄潤榛樺拷鐣?
        msg = f"绛栫暐鏂囦欢 {module_name} 鍔犺浇澶辫触锛岃Е鍙戝紓甯革細\n{traceback.format_exc()}"
        print(f"鉁?{msg}")
        self.write_log(_(msg))


def patched_run_backtesting(
    self,
    class_name: str,
    vt_symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    rate: float,
    slippage: float,
    size: int,
    pricetick: float,
    capital: int,
    setting: dict
) -> None:
    """
    娴佸紡鍥炴祴鐗堟湰锛岄伩鍏嶄竴娆℃€у姞杞藉叏閲忔暟鎹?
    """
    self.result_df = None
    self.result_statistics = None

    engine: BacktestingEngine = self.backtesting_engine
    engine.clear_data()

    if interval == Interval.TICK.value:
        from vnpy_ctastrategy.backtesting import BacktestingMode
        mode = BacktestingMode.TICK
    else:
        from vnpy_ctastrategy.backtesting import BacktestingMode
        mode = BacktestingMode.BAR

    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=interval,
        start=start,
        end=end,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        capital=capital,
        mode=mode
    )

    strategy_class: type[CtaTemplate] = self.classes[class_name]
    engine.add_strategy(strategy_class, setting)

    # 娴佸紡鍥炴祴锛氬垎鍧楀姞杞芥暟鎹?
    try:
        # 鍚姩绛栫暐
        engine.strategy.on_start()
        engine.strategy.trading = True

        # 瑙ｆ瀽鍚堢害
        symbol, exch = extract_vt_symbol(vt_symbol)
        exchange = Exchange(exch)

        # 鍒嗗潡鎷夊彇涓庡洖鏀?
        chunk_days = 15
        db: BaseDatabase = self.database
        cur_start = start
        total_bars = 0
        
        while cur_start <= end:
            cur_end = min(end, cur_start + timedelta(days=chunk_days))
            bars = db.load_bar_data(symbol, exchange, Interval(interval), cur_start, cur_end)
            
            for bar in bars:
                engine.new_bar(bar)
                total_bars += 1
            
            # 鍚?GUI 鎵撳嵃杩涘害
            try:
                pct = min(100, int((cur_end - start).days * 100 / max((end - start).days, 1)))
                self.write_log(_(f"娴佸紡鍥炴斁杩涘害锛歿pct}% {cur_start.date()}->{cur_end.date()} bars={len(bars)}"))
            except Exception:
                pass
            
            cur_start = cur_end + timedelta(minutes=1)

        engine.strategy.on_stop()
        self.write_log(_(f"娴佸紡鍥炴祴瀹屾垚锛屾€昏澶勭悊 {total_bars} 鏍筀绾?))
        
    except Exception:
        msg: str = _("绛栫暐鍥炴祴澶辫触锛岃Е鍙戝紓甯革細\n{}").format(traceback.format_exc())
        self.write_log(msg)
        self.thread = None
        return

    self.result_df = engine.calculate_result()
    self.result_statistics = engine.calculate_statistics(output=False)

    # Clear thread object handler.
    self.thread = None

    # Put backtesting done event
    event: Event = Event(EVENT_BACKTESTER_BACKTESTING_FINISHED)
    self.event_engine.put(event)


def patched_daily_result_add_trade(self, trade) -> None:
    """
    鍐呭瓨浼樺寲鐗堟湰鐨?DailyResult.add_trade
    """
    global MEMORY_OPTIMIZE_STATS

    if MEMORY_OPTIMIZE_STATS:
        # 鍐呭瓨浼樺寲妯″紡锛氬彧淇濆瓨缁熻鑱氬悎锛屼笉淇濆瓨瀹屾暣 TradeData 瀵硅薄
        # 鎵嬪姩鏇存柊缁熻淇℃伅锛岄伩鍏嶄繚瀛?TradeData 瀵硅薄
        from vnpy.trader.constant import Direction

        self.trade_count += 1

        # 璁＄畻鎴愪氦棰濆拰鎵嬬画璐癸紙杩欎簺鍦?calculate_pnl 涓細鐢ㄥ埌锛?
        # 娉ㄦ剰锛氳繖閲岄渶瑕佽闂?DailyResult 鐨勫叾浠栧睘鎬э紝浣嗘垜浠病鏈?size, rate, slippage
        # 鎵€浠ユ垜浠渶瑕佸湪 calculate_pnl 璋冪敤鏃朵紶鍏ヨ繖浜涘弬鏁?
        # 涓轰簡绠€鍖栵紝鎴戜滑鍏堣褰曞繀瑕佺殑缁熻淇℃伅
        if not hasattr(self, '_trade_stats'):
            self._trade_stats = {
                'total_volume': 0.0,
                'total_turnover': 0.0,
                'long_volume': 0.0,
                'short_volume': 0.0,
                'position_changes': []  # 鍙繚瀛樻寔浠撳彉鍖栵紝涓嶄繚瀛樺畬鏁村璞?
            }

        # 璁板綍鎸佷粨鍙樺寲
        if trade.direction == Direction.LONG:
            pos_change = trade.volume
            self._trade_stats['long_volume'] += trade.volume
        else:
            pos_change = -trade.volume
            self._trade_stats['short_volume'] += trade.volume

        self._trade_stats['position_changes'].append({
            'pos_change': pos_change,
            'price': trade.price,
            'volume': trade.volume
        })

        self._trade_stats['total_volume'] += trade.volume
        # turnover 璁＄畻闇€瑕?size锛岃繖閲屽厛璁板綍鍘熷鏁版嵁

    else:
        # 鏍囧噯妯″紡锛氫繚瀛樺畬鏁?TradeData 瀵硅薄
        self.trades.append(trade)


def patched_daily_result_calculate_pnl(
    self,
    pre_close: float,
    start_pos: float,
    size: float,
    rate: float,
    slippage: float
) -> None:
    """
    鍐呭瓨浼樺寲鐗堟湰鐨?DailyResult.calculate_pnl
    """
    global MEMORY_OPTIMIZE_STATS

    # If no pre_close provided on the first day, use value 1 to avoid zero division error
    if pre_close:
        self.pre_close = pre_close
    else:
        self.pre_close = 1

    # Holding pnl is the pnl from holding position at day start
    self.start_pos = start_pos
    self.end_pos = start_pos

    self.holding_pnl = self.start_pos * (self.close_price - self.pre_close) * size

    if MEMORY_OPTIMIZE_STATS and hasattr(self, '_trade_stats'):
        # 鍐呭瓨浼樺寲妯″紡锛氫娇鐢ㄨ仛鍚堢粺璁¤绠?
        self.trade_count = len(self._trade_stats['position_changes'])

        for trade_stat in self._trade_stats['position_changes']:
            pos_change = trade_stat['pos_change']
            price = trade_stat['price']
            volume = trade_stat['volume']

            self.end_pos += pos_change

            turnover = volume * size * price
            self.trading_pnl += pos_change * (self.close_price - price) * size
            self.slippage += volume * size * slippage

            self.turnover += turnover
            self.commission += turnover * rate
    else:
        # 鏍囧噯妯″紡锛氫娇鐢ㄥ畬鏁?trades 鍒楄〃
        from vnpy.trader.constant import Direction

        self.trade_count = len(self.trades)

        for trade in self.trades:
            if trade.direction == Direction.LONG:
                pos_change = trade.volume
            else:
                pos_change = -trade.volume

            self.end_pos += pos_change

            turnover = trade.volume * size * trade.price
            self.trading_pnl += pos_change * (self.close_price - trade.price) * size
            self.slippage += trade.volume * size * slippage

            self.turnover += turnover
            self.commission += turnover * rate

    # Net pnl takes account of commission and slippage cost
    self.total_pnl = self.trading_pnl + self.holding_pnl
    self.net_pnl = self.total_pnl - self.commission - self.slippage


def apply_patches():
    """
    搴旂敤鎵€鏈夎ˉ涓?
    """
    print("=== 搴旂敤 VN.PY CTA 鍥炴祴寮曟搸琛ヤ竵 ===")
    
    # 琛ヤ竵1: 淇绛栫暐鍔犺浇闂
    BacktesterEngine.load_strategy_class = patched_load_strategy_class
    BacktesterEngine.load_strategy_class_from_folder = patched_load_strategy_class_from_folder
    BacktesterEngine.load_strategy_class_from_module = patched_load_strategy_class_from_module
    print("鉁?宸插簲鐢ㄧ瓥鐣ュ姞杞戒慨澶嶈ˉ涓?")
    
    # 琛ヤ竵2: 娴佸紡鍥炴祴
    BacktesterEngine.run_backtesting = patched_run_backtesting
    print("鉁?宸插簲鐢ㄦ祦寮忓洖娴嬭ˉ涓?")
    
    # 琛ヤ竵3: 鍐呭瓨浼樺寲缁熻锛堝彲閫夛級
    DailyResult.add_trade = patched_daily_result_add_trade
    DailyResult.calculate_pnl = patched_daily_result_calculate_pnl
    print("鉁?宸插簲鐢ㄥ唴瀛樹紭鍖栫粺璁¤ˉ涓?")
    
    print("=== 琛ヤ竵搴旂敤瀹屾垚 ===")


def set_memory_optimize_stats(enabled: bool):
    """
    璁剧疆鍐呭瓨浼樺寲缁熻寮€鍏?
    """
    global MEMORY_OPTIMIZE_STATS
    MEMORY_OPTIMIZE_STATS = enabled
    print(f"鍐呭瓨浼樺寲缁熻: {'寮€鍚? if enabled else '鍏抽棴'}")


def patched_backtester_manager_init_ui(self) -> None:
    """
    淇鐗堟湰鐨?BacktesterManager.init_ui锛屾坊鍔犲唴瀛樹紭鍖栫粺璁″閫夋
    """
    # 璋冪敤鍘熷鐨?init_ui 鏂规硶
    original_init_ui(self)

    # 娣诲姞鍐呭瓨浼樺寲缁熻澶嶉€夋鍒拌〃鍗曚腑
    try:
        from PySide6 import QtWidgets

        # 鎵惧埌琛ㄥ崟甯冨眬
        left_widget = self.findChild(QtWidgets.QWidget)
        if left_widget:
            layout = left_widget.layout()
            if isinstance(layout, QtWidgets.QVBoxLayout):
                # 鍦ㄨ〃鍗曚腑鎵惧埌 QFormLayout
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and isinstance(item.layout(), QtWidgets.QFormLayout):
                        form_layout = item.layout()

                        # 娣诲姞鍐呭瓨浼樺寲缁熻澶嶉€夋
                        self.memory_optimize_checkbox = QtWidgets.QCheckBox()
                        self.memory_optimize_checkbox.setChecked(False)  # 榛樿鍏抽棴
                        self.memory_optimize_checkbox.setToolTip(
                            "寮€鍚悗灏嗕笉淇濆瓨瀹屾暣鐨勬垚浜よ褰曪紝鍙樉钁楅檷浣庡唴瀛樺崰鐢紝浣嗘棤娉曟煡鐪嬮€愮瑪鎴愪氦鏄庣粏"
                        )

                        form_layout.addRow("鍐呭瓨浼樺寲缁熻", self.memory_optimize_checkbox)
                        print("鉁?宸叉坊鍔犲唴瀛樹紭鍖栫粺璁″閫夋鍒?GUI")
                        break
    except Exception as e:
        print(f"鉁?娣诲姞鍐呭瓨浼樺寲缁熻澶嶉€夋澶辫触: {e}")


def patched_backtester_manager_start_backtesting(self) -> None:
    """
    淇鐗堟湰鐨?BacktesterManager.start_backtesting锛屼紶閫掑唴瀛樹紭鍖栨爣蹇?
    """
    # 妫€鏌ュ唴瀛樹紭鍖栧閫夋鐘舵€?
    memory_optimize = False
    if hasattr(self, 'memory_optimize_checkbox'):
        memory_optimize = self.memory_optimize_checkbox.isChecked()

    # 璁剧疆鍏ㄥ眬鏍囧織
    set_memory_optimize_stats(memory_optimize)

    # 璋冪敤鍘熷鐨?start_backtesting 鏂规硶
    return original_start_backtesting(self)

# 鏁板瓧鏍煎紡鍖栧伐鍏峰嚱鏁?

def format_number(value: float) -> str:
    """
    鏍煎紡鍖栨暟瀛椾负鏇村弸濂界殑鏄剧ず鏍煎紡
    """
    if abs(value) >= 1e8:  # 浜跨骇鍒?
        return f"{value/1e8:.1f}浜?"
    elif abs(value) >= 1e4:  # 涓囩骇鍒?
        return f"{value/1e4:.1f}涓?"
    elif abs(value) >= 1000:  # 鍗冪骇鍒?
        return f"{value:,.0f}"
    elif abs(value) >= 1:
        return f"{value:.2f}"
    elif abs(value) >= 0.01:
        return f"{value:.3f}"
    else:
        return f"{value:.6f}"


class CustomAxisItem:
    """
    鑷畾涔夎酱椤圭洰锛屾彁渚涙洿濂界殑鏁板瓧鏍煎紡鍖?
    """
    @staticmethod
    def tickStrings(values, scale, spacing):
        """
        鏍煎紡鍖栧潗鏍囪酱鍒诲害鏍囩
        """
        strings = []
        for v in values:
            if isinstance(v, (int, float)):
                strings.append(format_number(v))
            else:
                strings.append(str(v))
        return strings


def patched_backtester_chart_init_ui(self) -> None:
    """
    淇鐗堟湰鐨?BacktesterChart.init_ui锛屾坊鍔犺嚜瀹氫箟鏁板瓧鏍煎紡鍖?
    """
    import pyqtgraph as pg
    
    pg.setConfigOptions(antialias=True)

    # 鍒涘缓鑷畾涔夎酱
    class FormattedAxisItem(pg.AxisItem):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        def tickStrings(self, values, scale, spacing):
            return CustomAxisItem.tickStrings(values, scale, spacing)

    # Create plot widgets with custom axis
    self.balance_plot = self.addPlot(
        title=_("璐︽埛鍑€鍊?"),
        axisItems={
            "bottom": DateAxis(self.dates, orientation="bottom"),
            "left": FormattedAxisItem(orientation="left")
        }
    )
    self.nextRow()

    self.drawdown_plot = self.addPlot(
        title=_("鍑€鍊煎洖鎾?"),
        axisItems={
            "bottom": DateAxis(self.dates, orientation="bottom"),
            "left": FormattedAxisItem(orientation="left")
        }
    )
    self.nextRow()

    self.pnl_plot = self.addPlot(
        title=_("姣忔棩鐩堜簭"),
        axisItems={
            "bottom": DateAxis(self.dates, orientation="bottom"),
            "left": FormattedAxisItem(orientation="left")
        }
    )
    self.nextRow()

    self.distribution_plot = self.addPlot(
        title=_("鐩堜簭鍒嗗竷"),
        axisItems={
            "bottom": FormattedAxisItem(orientation="bottom"),
            "left": FormattedAxisItem(orientation="left")
        }
    )

    # Add curves and bars on plot widgets (淇濇寔鍘熸湁鐨勭粯鍥鹃厤缃?
    self.balance_curve = self.balance_plot.plot(
        pen=pg.mkPen("#ffc107", width=3)
    )

    dd_color: str = "#303f9f"
    self.drawdown_curve = self.drawdown_plot.plot(
        fillLevel=-0.3, brush=dd_color, pen=dd_color
    )

    profit_color: str = 'r'
    loss_color: str = 'g'
    self.profit_pnl_bar = pg.BarGraphItem(
        x=[], height=[], width=0.3, brush=profit_color, pen=profit_color
    )
    self.loss_pnl_bar = pg.BarGraphItem(
        x=[], height=[], width=0.3, brush=loss_color, pen=loss_color
    )
    self.pnl_plot.addItem(self.profit_pnl_bar)
    self.pnl_plot.addItem(self.loss_pnl_bar)

    distribution_color: str = "#6d4c41"
    self.distribution_curve = self.distribution_plot.plot(
        fillLevel=-0.3, brush=distribution_color, pen=distribution_color
    )

# 淇濆瓨鍘熷鏂规硶鐨勫紩鐢?
original_init_ui = None
original_start_backtesting = None
original_chart_init_ui = None


def apply_gui_patches():
    """
    搴旂敤 GUI 鐩稿叧琛ヤ竵
    """
    global original_init_ui, original_start_backtesting, original_chart_init_ui

    try:
        from vnpy_ctabacktester.ui.widget import BacktesterManager, BacktesterChart

        # 淇濆瓨鍘熷鏂规硶
        original_init_ui = BacktesterManager.init_ui
        original_start_backtesting = BacktesterManager.start_backtesting

        # 搴旂敤琛ヤ竵
        BacktesterManager.init_ui = patched_backtester_manager_init_ui
        BacktesterManager.start_backtesting = patched_backtester_manager_start_backtesting

        print("鉁?宸插簲鐢?GUI 鍐呭瓨浼樺寲缁熻琛ヤ竵")
        
        # 搴旂敤鍥捐〃鏍煎紡鍖栬ˉ涓?
        original_chart_init_ui = BacktesterChart.init_ui
        BacktesterChart.init_ui = patched_backtester_chart_init_ui
        print("鉁?宸插簲鐢ㄥ浘琛ㄦ暟瀛楁牸寮忓寲琛ヤ竵")
        
    except Exception as e:
        print(f"鉁?GUI 琛ヤ竵搴旂敤澶辫触: {e}")

# 鑷姩搴旂敤琛ヤ竵
if __name__ == "__main__":
    apply_patches()
    apply_gui_patches()
else:
    # 浣滀负妯″潡瀵煎叆鏃惰嚜鍔ㄥ簲鐢ㄨˉ涓?
    apply_patches()
    apply_gui_patches()
