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
        /* 移动端优化：右侧栏在窄屏时自动折叠至下方 */
        @media (max-width: 720px){
          .two-col {flex-direction: column;}
        }
        """
    ) as demo:
        gr.Markdown("## 棋类对战平台（五子棋 / 围棋 / 黑白棋 + AI + 录像回放）")

        with gr.Row(elem_classes=["two-col"]):
            # 左侧主区域
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

                with gr.Row():
                    save_path = gr.Textbox(label="保存文件名", placeholder="save.json", scale=3)
                    btn_save = gr.Button("保存", scale=1)
                    load_path = gr.Textbox(label="读取文件名", placeholder="save.json", scale=3)
                    btn_load = gr.Button("读取", scale=1)

            # 右侧栏：三个独立下拉框（默认均收起）
            with gr.Column(scale=2):
                # 1) 设置与提示
                with gr.Accordion("设置与提示（可收起/展开）", open=False):
                    with gr.Group():
                        game_type = gr.Radio(choices=["围棋", "五子棋", "黑白棋"], value="围棋", label="游戏类型")
                        size = gr.Slider(8, 19, value=19, step=1, label="棋盘大小（黑白棋推荐偶数，默认8）")
                        komi = gr.Number(value=7.5, label="贴目（仅围棋，白贴目）")
                        theme = gr.Dropdown(choices=["wood","light"], value="wood", label="主题")
                    gr.Markdown("### 提示信息与状态预览")
                    status = gr.Image(label="状态预览", interactive=False, type="pil", height=160)
                    gr.Markdown(
                        '<div class="footer-note">提示：'
                        '围棋使用“虚着”两次进入结算；'
                        '黑白棋若当前无合法着法将自动跳过一回合；'
                        '保存/读取时会携带录像（若启用）。'
                        '</div>'
                    )

                # 2) AI 设置（默认收起）
                with gr.Accordion("AI 设置（可收起/展开）", open=False):
                    gr.Markdown("当前仅黑白棋启用 AI。选择其他棋种时将自动降级为玩家对战。")
                    with gr.Group():
                        black_side = gr.Radio(choices=["玩家", "AI"], value="玩家", label="黑方控制")
                        white_side = gr.Radio(choices=["玩家", "AI"], value="玩家", label="白方控制")
                        ai_kind = gr.Dropdown(choices=["Reversi"], value="Reversi", label="AI 类型")
                        ai_level = gr.Radio(choices=["1","2"], value="1", label="AI 级别（1随机 / 2启发式）")

                # 3) 录像与回放（默认收起）
                with gr.Accordion("录像与回放（可收起/展开）", open=False):
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
                    gr.Markdown(
                        '<div class="footer-note">'
                        '读取含录像的存档可直接回放；'
                        '也可在当前对局点击“进入回放模式”从现有录像进入回放。'
                        '</div>'
                    )

        # 事件绑定
        def start_game(gt, sz, km, th, bs, ws, ak, alv):
            ctl.set_theme(th)
            img = ctl.new_game(gt, int(sz), float(km), bs, ws, ak, int(alv))
            return img, img

        btn_new.click(
            start_game,
            inputs=[game_type, size, komi, theme, black_side, white_side, ai_kind, ai_level],
            outputs=[canvas, status]
        )

        def on_click(evt: gr.SelectData):
            img, popup = ctl.click_canvas(evt)
            if popup:
                gr.Warning(popup)
            return img, img

        canvas.select(on_click, outputs=[canvas, status])

        def on_pass():
            img, popup = ctl.do_pass()
            if popup:
                gr.Warning(popup)
            return img, img

        def on_resign():
            img, popup = ctl.resign()
            if popup:
                gr.Warning(popup)
            return img, img

        def on_undo():
            img, popup = ctl.undo()
            if popup:
                gr.Warning(popup)
            return img, img

        btn_pass.click(on_pass, outputs=[canvas, status])
        btn_resign.click(on_resign, outputs=[canvas, status])
        btn_undo.click(on_undo, outputs=[canvas, status])

        def on_save(p):
            img, popup = ctl.save(p)
            if popup:
                gr.Warning(popup)
            return img, img

        def on_load(p):
            img, popup = ctl.load(p)
            if popup:
                gr.Warning(popup)
            return img, img

        btn_save.click(on_save, inputs=[save_path], outputs=[canvas, status])
        btn_load.click(on_load, inputs=[load_path], outputs=[canvas, status])

        # 录像与回放控制
        def on_record_toggle(v):
            img, popup = ctl.replay_toggle_record(v)
            if popup:
                gr.Warning(popup)
            return img, img
        record_toggle.change(on_record_toggle, inputs=[record_toggle], outputs=[canvas, status])

        def on_replay_enter():
            img, popup = ctl.replay_enter_from_current()
            if popup:
                gr.Warning(popup)
            return img, img
        btn_replay_enter.click(on_replay_enter, outputs=[canvas, status])

        def on_replay_start():
            img, popup = ctl.replay_start()
            if popup:
                gr.Warning(popup)
            return img, img
        btn_replay_start.click(on_replay_start, outputs=[canvas, status])

        def on_replay_pause():
            img, popup = ctl.replay_pause()
            if popup:
                gr.Warning(popup)
            return img, img
        btn_replay_pause.click(on_replay_pause, outputs=[canvas, status])

        def on_replay_stop():
            img, popup = ctl.replay_stop()
            if popup:
                gr.Warning(popup)
            return img, img
        btn_replay_stop.click(on_replay_stop, outputs=[canvas, status])

        def on_replay_prev():
            img, popup = ctl.replay_prev()
            if popup:
                gr.Warning(popup)
            return img, img
        btn_replay_prev.click(on_replay_prev, outputs=[canvas, status])

        def on_replay_next():
            img, popup = ctl.replay_next()
            if popup:
                gr.Warning(popup)
            return img, img
        btn_replay_next.click(on_replay_next, outputs=[canvas, status])

        def on_speed(v):
            img, popup = ctl.replay_set_speed(v)
            if popup:
                gr.Info(popup)
            return img, img
        replay_speed.change(on_speed, inputs=[replay_speed], outputs=[canvas, status])

        # 初始加载默认 19x19 围棋
        def _init():
            ctl.set_theme("wood")
            img = ctl.new_game("围棋", 19, 7.5, "玩家", "玩家", "Reversi", 1)
            return img, img

        demo.load(_init, outputs=[canvas, status])

    return demo