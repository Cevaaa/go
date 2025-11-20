from __future__ import annotations
import gradio as gr
from .controller import UIController

def build_app():
    ctl = UIController()

    with gr.Blocks(title="棋类对战平台", theme=gr.themes.Soft(), css="""
    .footer-note {font-size: 12px; color: #666;}
    .wide-row {display:flex; gap: 12px; flex-wrap: wrap;}
    .grow {flex:1;}
    """) as demo:
        gr.Markdown("## 棋类对战平台（五子棋 / 围棋）")
        with gr.Row():
            with gr.Column(scale=3):
                canvas = gr.Image(label="棋盘", value=None, interactive=True, type="pil", height=640)
                with gr.Row():
                    btn_pass = gr.Button("虚着（围棋）", variant="secondary")
                    btn_undo = gr.Button("悔棋")
                    btn_resign = gr.Button("认负")
                with gr.Row():
                    save_path = gr.Textbox(label="保存文件名", placeholder="save.json", scale=3)
                    btn_save = gr.Button("保存", scale=1)
                    load_path = gr.Textbox(label="读取文件名", placeholder="save.json", scale=3)
                    btn_load = gr.Button("读取", scale=1)
                gr.Markdown('<div class="footer-note">提示：点击棋盘交点落子；围棋使用“虚着”两次进入结算；可保存/读取局面。</div>')
            with gr.Column(scale=2):
                with gr.Group():
                    game_type = gr.Radio(choices=["围棋", "五子棋"], value="围棋", label="游戏类型")
                    size = gr.Slider(8, 19, value=19, step=1, label="棋盘大小")
                    komi = gr.Number(value=7.5, label="贴目（围棋，白贴目）")
                    theme = gr.Dropdown(choices=["wood","light"], value="wood", label="主题")
                    btn_new = gr.Button("开始新对局", variant="primary")
                gr.Markdown("### 当前状态/消息")
                status = gr.Image(label="状态预览", interactive=False, type="pil", height=160)
                gr.Markdown("如需隐藏提示，可收起右侧设置区域。")

        # events
        def start_game(gt, sz, km, th):
            img = ctl.new_game(gt, int(sz), float(km))
            ctl.theme = th
            return img, img

        btn_new.click(start_game, inputs=[game_type, size, komi, theme], outputs=[canvas, status])

        def on_click(evt: gr.SelectData):
            img = ctl.click_canvas(evt)
            return img, img

        canvas.select(on_click, outputs=[canvas, status])

        btn_pass.click(lambda: (ctl.do_pass(), ctl.get_image()), outputs=[canvas, status])
        btn_resign.click(lambda: (ctl.resign(), ctl.get_image()), outputs=[canvas, status])
        btn_undo.click(lambda: (ctl.undo(), ctl.get_image()), outputs=[canvas, status])

        btn_save.click(lambda p: (ctl.save(p), ctl.get_image()), inputs=[save_path], outputs=[canvas, status])
        btn_load.click(lambda p: (ctl.load(p), ctl.get_image()), inputs=[load_path], outputs=[canvas, status])

    return demo