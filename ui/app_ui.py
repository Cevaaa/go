from __future__ import annotations
import gradio as gr
from .controller import UIController

def build_app():
    ctl = UIController()

    with gr.Blocks(
        title="棋类对战平台",
        theme=gr.themes.Soft(),
        css="""
        .footer-note {font-size: 12px; color: #666;}
        .wide-row {display:flex; gap: 12px; flex-wrap: wrap;}
        .grow {flex:1;}
        @media (max-width: 720px){
          .two-col {flex-direction: column;}
        }
        """
    ) as demo:
        gr.Markdown("## 棋类对战平台（五子棋 / 围棋 / 黑白棋）")

        with gr.Row(elem_classes=["two-col"]):
            # 左侧主区域：棋盘 + 基础操作
            with gr.Column(scale=3):
                canvas = gr.Image(
                    label="棋盘",
                    value=None,
                    interactive=True,
                    type="pil",
                    height=640
                )
                with gr.Row():
                    btn_pass = gr.Button("虚着（围棋）", variant="secondary")
                    btn_undo = gr.Button("悔棋")
                    btn_resign = gr.Button("认负")
                with gr.Row():
                    btn_new = gr.Button("开始新对局", variant="primary")

            # 右侧栏：多个折叠区
            with gr.Column(scale=2):
                # 用户账户
                with gr.Accordion("用户账户（登录/战绩）", open=True):
                    gr.Markdown("### 登录/注册")
                    with gr.Row():
                        username = gr.Textbox(label="用户名", placeholder="例如 alice", scale=1)
                        password = gr.Textbox(label="密码", type="password", scale=1)
                    with gr.Row():
                        btn_login = gr.Button("登录", variant="primary")
                        btn_register = gr.Button("注册")
                        btn_logout = gr.Button("登出")
                    gr.Markdown("### 当前对局双方")
                    battle_info = gr.Markdown("Black: 游客  |  White: 游客")
                    btn_refresh_battle = gr.Button("刷新对局信息")

                # AI 设置（独立折叠区）：合并身份与 AI 控制
                with gr.Accordion("AI 设置（控制方统一：玩家 / 当前用户 / AI）", open=True):
                    with gr.Group():
                        side_black = gr.Radio(choices=["玩家","当前用户","AI"], value="玩家", label="黑方控制")
                        side_white = gr.Radio(choices=["玩家","当前用户","AI"], value="玩家", label="白方控制")
                        ai_kind = gr.Dropdown(choices=["Reversi"], value="Reversi", label="AI 类型（仅黑白棋生效）")
                        ai_level = gr.Radio(choices=["1","2"], value="1", label="AI 级别（1随机 / 2启发式）")

                # 设置与提示
                with gr.Accordion("设置与提示", open=False):
                    with gr.Group():
                        game_type = gr.Radio(choices=["围棋", "五子棋", "黑白棋"], value="围棋", label="游戏类型")
                        size = gr.Slider(8, 19, value=19, step=1, label="棋盘大小（黑白棋推荐偶数，默认8）")
                        komi = gr.Number(value=7.5, label="贴目（仅围棋，白贴目）")
                        theme = gr.Dropdown(choices=["wood","light"], value="wood", label="主题")
                    status = gr.Image(label="状态预览", interactive=False, type="pil", height=160)
                    gr.Markdown(
                        '<div class="footer-note">提示：'
                        '围棋使用“虚着”两次进入结算；'
                        '黑白棋若当前无合法着法将自动跳过；'
                        '仅黑白棋启用 AI；'
                        '保存/读取在“存档管理”中。'
                        '</div>'
                    )

                # 存档管理（移至右侧）
                with gr.Accordion("存档管理", open=False):
                    save_path = gr.Textbox(label="保存文件名", placeholder="save.json")
                    btn_save = gr.Button("保存")
                    load_path = gr.Textbox(label="读取文件名", placeholder="save.json")
                    btn_load = gr.Button("读取")

                # 录像与回放
                with gr.Accordion("录像与回放", open=False):
                    record_toggle = gr.Checkbox(value=True, label="启用录像（新对局默认开启）")
                    with gr.Row():
                        btn_replay_enter = gr.Button("进入回放模式", variant="secondary")
                        btn_replay_start = gr.Button("开始/继续")
                        btn_replay_pause = gr.Button("暂停")
                        btn_replay_stop = gr.Button("停止")
                    with gr.Row():
                        btn_replay_prev = gr.Button("上一步")
                        btn_replay_next = gr.Button("下一步")
                        replay_speed = gr.Slider(0.25, 4.0, value=1.0, step=0.25, label="回放速度（倍速）")

        # ---------------- 事件绑定 ----------------

        def start_game(gt, sz, km, th, ak, alv):
            # 设置主题 -> 新局
            ctl.set_theme(th)
            img = ctl.new_game(gt, int(sz), float(km), ak, int(alv))
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"

        btn_new.click(
            start_game,
            inputs=[game_type, size, komi, theme, ai_kind, ai_level],
            outputs=[canvas, status, battle_info]
        )

        # 棋盘点击
        def on_click(evt: gr.SelectData):
            img, popup = ctl.click_canvas(evt)
            if popup: gr.Warning(popup)
            return img, img
        canvas.select(on_click, outputs=[canvas, status])

        # 基础动作
        def on_pass():
            img, popup = ctl.do_pass()
            if popup: gr.Warning(popup)
            return img, img
        def on_resign():
            img, popup = ctl.resign()
            if popup: gr.Warning(popup)
            return img, img
        def on_undo():
            img, popup = ctl.undo()
            if popup: gr.Warning(popup)
            return img, img
        btn_pass.click(on_pass, outputs=[canvas, status])
        btn_resign.click(on_resign, outputs=[canvas, status])
        btn_undo.click(on_undo, outputs=[canvas, status])

        # 存档管理
        def on_save(p):
            img, popup = ctl.save(p)
            if popup: gr.Warning(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        def on_load(p):
            img, popup = ctl.load(p)
            if popup: gr.Warning(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        btn_save.click(on_save, inputs=[save_path], outputs=[canvas, status, battle_info])
        btn_load.click(on_load, inputs=[load_path], outputs=[canvas, status, battle_info])

        # 用户账户
        def on_login(u, p):
            img, popup = ctl.account_login(u, p)
            if popup: gr.Info(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        def on_register(u, p):
            img, popup = ctl.account_register(u, p)
            if popup: gr.Info(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        def on_logout():
            img, popup = ctl.account_logout()
            if popup: gr.Info(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        btn_login.click(on_login, inputs=[username, password], outputs=[canvas, status, battle_info])
        btn_register.click(on_register, inputs=[username, password], outputs=[canvas, status, battle_info])
        btn_logout.click(on_logout, outputs=[canvas, status, battle_info])

        # 控制方（统一三选一）
        def on_set_black(v):
            img, popup = ctl.set_side_control("black", v)
            if popup: gr.Info(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        def on_set_white(v):
            img, popup = ctl.set_side_control("white", v)
            if popup: gr.Info(popup)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        side_black.change(on_set_black, inputs=[side_black], outputs=[canvas, status, battle_info])
        side_white.change(on_set_white, inputs=[side_white], outputs=[canvas, status, battle_info])

        # AI 级别
        def on_ai_level(v):
            img, popup = ctl.set_ai_level(int(v))
            if popup: gr.Info(popup)
            return img, img
        ai_level.change(on_ai_level, inputs=[ai_level], outputs=[canvas, status])

        # 刷新对局信息
        def on_refresh_battle():
            info = ctl.battle_info()
            return f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        btn_refresh_battle.click(on_refresh_battle, outputs=[battle_info])

        # 录像与回放
        def on_record_toggle(v):
            img, popup = ctl.replay_toggle_record(v)
            if popup: gr.Warning(popup)
            return img, img
        record_toggle.change(on_record_toggle, inputs=[record_toggle], outputs=[canvas, status])

        def on_replay_enter():
            img, popup = ctl.replay_enter_from_current()
            if popup: gr.Warning(popup)
            return img, img
        btn_replay_enter.click(on_replay_enter, outputs=[canvas, status])

        def on_replay_start():
            img, popup = ctl.replay_start()
            if popup: gr.Warning(popup)
            return img, img
        btn_replay_start.click(on_replay_start, outputs=[canvas, status])

        def on_replay_pause():
            img, popup = ctl.replay_pause()
            if popup: gr.Warning(popup)
            return img, img
        btn_replay_pause.click(on_replay_pause, outputs=[canvas, status])

        def on_replay_stop():
            img, popup = ctl.replay_stop()
            if popup: gr.Warning(popup)
            return img, img
        btn_replay_stop.click(on_replay_stop, outputs=[canvas, status])

        def on_replay_prev():
            img, popup = ctl.replay_prev()
            if popup: gr.Warning(popup)
            return img, img
        btn_replay_prev.click(on_replay_prev, outputs=[canvas, status])

        def on_replay_next():
            img, popup = ctl.replay_next()
            if popup: gr.Warning(popup)
            return img, img
        btn_replay_next.click(on_replay_next, outputs=[canvas, status])

        def on_speed(v):
            img, popup = ctl.replay_set_speed(v)
            if popup: gr.Info(popup)
            return img, img
        replay_speed.change(on_speed, inputs=[replay_speed], outputs=[canvas, status])

        # 初始默认局面
        def _init():
            ctl.set_theme("wood")
            img = ctl.new_game("围棋", 19, 7.5, "Reversi", 1)
            info = ctl.battle_info()
            return img, img, f"Black: {info['black']['label']}  |  White: {info['white']['label']}"
        demo.load(_init, outputs=[canvas, status, battle_info])

    return demo