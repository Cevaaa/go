import gradio as gr
from ui.app_ui import build_app

def main():
    demo = build_app()
    demo.queue().launch()

if __name__ == "__main__":
    main()
