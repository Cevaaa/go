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
                # 取消用户上传能力，移除源图上传，保持仅渲染输出与点击
                canvas = gr.Image(
                    label="棋盘",
                    value=None,            # 初次加载时，start_game 会填充默认 19x19 围棋盘
                    interactive=True,
                    type="pil",
                    height=640
                )
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

        # 为了解决主题需要点击两次的问题：先设置主题到控制器，再创建新对局
        def start_game(gt, sz, km, th):
            # 先更新主题
            ctl.set_theme(th)
            # 再创建新对局并返回图像
            img = ctl.new_game(gt, int(sz), float(km))
            return img, img

        btn_new.click(start_game, inputs=[game_type, size, komi, theme], outputs=[canvas, status])

        def on_click(evt: gr.SelectData):
            img, popup = ctl.click_canvas(evt)
            # 利用 Gradio 的通知系统显示弹窗
            if popup:
                gr.Warning(popup)  # 仅用于弹窗消息，中文
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

        # 默认渲染一次 19x19 围棋盘，满足“先默认渲染一副19*19的围棋棋盘”
        # 页面加载时自动创建默认对局
        def _init():
            ctl.set_theme("wood")
            img = ctl.new_game("围棋", 19, 7.5)
            return img, img

        demo.load(_init, outputs=[canvas, status])

    return demo