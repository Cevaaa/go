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
        gr.Markdown("## 棋类对战平台（五子棋 / 围棋 / 黑白棋）")

        # 顶层两列布局：左（棋盘与操作），右（可隐藏设置边栏与提示信息）
        with gr.Row(elem_classes=["two-col"]):
            # 左侧主区域
            with gr.Column(scale=3):
                # 棋盘画布（仅渲染输出与点击，不上传外部图）
                canvas = gr.Image(
                    label="棋盘",
                    value=None,            # 页面加载时通过 _init() 自动填充默认 19x19 围棋盘
                    interactive=True,
                    type="pil",
                    height=640
                )

                # 操作按钮第一行
                with gr.Row():
                    btn_pass = gr.Button("虚着（围棋）", variant="secondary")
                    btn_undo = gr.Button("悔棋")
                    btn_resign = gr.Button("认负")

                # “开始新对局”按钮位于三按钮正下方（单独一行）
                with gr.Row():
                    btn_new = gr.Button("开始新对局", variant="primary")

                # 存读盘一行
                with gr.Row():
                    save_path = gr.Textbox(label="保存文件名", placeholder="save.json", scale=3)
                    btn_save = gr.Button("保存", scale=1)
                    load_path = gr.Textbox(label="读取文件名", placeholder="save.json", scale=3)
                    btn_load = gr.Button("读取", scale=1)

            # 右侧设置边栏（可隐藏）
            with gr.Column(scale=2):
                # 使用 Accordion 可折叠隐藏侧边栏，默认展开
                with gr.Accordion("设置与提示（可收起/展开）", open=True):
                    with gr.Group():
                        game_type = gr.Radio(choices=["围棋", "五子棋", "黑白棋"], value="围棋", label="游戏类型")
                        size = gr.Slider(8, 19, value=19, step=1, label="棋盘大小（黑白棋推荐偶数，默认8）")
                        komi = gr.Number(value=7.5, label="贴目（仅围棋，白贴目）")
                        theme = gr.Dropdown(choices=["wood","light"], value="wood", label="主题")
                    # 将“提示信息/状态”放入侧边栏中
                    gr.Markdown("### 提示信息与状态预览")
                    status = gr.Image(label="状态预览", interactive=False, type="pil", height=160)
                    gr.Markdown(
                        '<div class="footer-note">提示：'
                        '点击棋盘交点落子；围棋使用“虚着”两次进入结算；'
                        '黑白棋若当前无合法着法将自动跳过一回合；可保存/读取局面。'
                        '</div>'
                    )

        # 事件绑定
        # 为保持第二版对“主题需要点两次”的修复：先 set_theme 再 new_game
        def start_game(gt, sz, km, th):
            ctl.set_theme(th)
            # 如果选择黑白棋且大小为奇数，仍可运行；推荐用户选 8/10/12 等偶数
            img = ctl.new_game(gt, int(sz), float(km))
            return img, img

        # 注意：开始新对局按钮位于左侧三按钮正下方，因此 inputs 从右侧设置里取值
        btn_new.click(start_game, inputs=[game_type, size, komi, theme], outputs=[canvas, status])

        def on_click(evt: gr.SelectData):
            img, popup = ctl.click_canvas(evt)
            if popup:
                gr.Warning(popup)  # 中文弹窗
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

        # 页面加载时自动初始化默认 19×19 围棋盘
        def _init():
            ctl.set_theme("wood")
            img = ctl.new_game("围棋", 19, 7.5)
            return img, img

        demo.load(_init, outputs=[canvas, status])

    return demo