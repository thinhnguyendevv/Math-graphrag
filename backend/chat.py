from __future__ import annotations

from pathlib import Path
import traceback

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from math_graphrag.config import load_config
from math_graphrag.embedding import get_embedding_model
from math_graphrag.llm import LLMQuotaError, get_llm
from math_graphrag.neo4j_store import Neo4jGraphStore
from math_graphrag.retrieval import GraphRAGRetriever

console = Console()


def build_retriever(config_path: str = "configs/config.yaml") -> GraphRAGRetriever:
    config = load_config(Path(config_path))
    llm = get_llm(config)
    embedding_model = get_embedding_model(config)
    store = Neo4jGraphStore(config)
    return GraphRAGRetriever(config=config, store=store, llm=llm, embedding_model=embedding_model)


def print_sources(sources: list[dict]):
    if not sources:
        console.print(Panel("Không có nguồn rõ ràng được trả về.", title="Nguồn", border_style="yellow"))
        return

    table = Table(title="Nguồn tham khảo", box=box.ROUNDED, show_lines=True)
    table.add_column("STT", justify="center", style="cyan", width=5)
    table.add_column("Mục / Heading", style="white")
    table.add_column("Trang", justify="center", style="green", width=14)
    table.add_column("Score", justify="center", style="magenta", width=10)
    table.add_column("Preview", style="dim", overflow="fold")

    for i, src in enumerate(sources, start=1):
        heading = src.get("heading_path") or "Không rõ mục"
        page_start = src.get("page_start")
        page_end = src.get("page_end")
        if page_start and page_end and page_start != page_end:
            page_text = f"{page_start}-{page_end}"
        elif page_start:
            page_text = str(page_start)
        else:
            page_text = "?"
        score = src.get("score")
        score_text = f"{score:.4f}" if isinstance(score, (int, float)) else "-"
        preview = src.get("text_preview") or ""
        if len(preview) > 250:
            preview = preview[:250] + "..."
        table.add_row(str(i), heading, page_text, score_text, preview)
    console.print(table)


def print_graph_paths(graph_paths: list[dict]):
    if not graph_paths:
        return
    table = Table(title="Graph paths liên quan", box=box.ROUNDED, show_lines=True)
    table.add_column("STT", justify="center", style="cyan", width=5)
    table.add_column("Đường đi tri thức", style="white")
    table.add_column("Quan hệ", style="green")
    for i, item in enumerate(graph_paths, start=1):
        path = item.get("path", [])
        path_text = " → ".join(str(x) for x in path) if isinstance(path, list) else str(path)
        table.add_row(str(i), path_text, str(item.get("relation", "")))
    console.print(table)



def print_query_understanding(qu: dict):
    if not qu:
        return
    lines = []
    if qu.get("intent"):
        lines.append(f"[bold]Intent:[/bold] {qu.get('intent')}")
    if qu.get("rewritten_query"):
        lines.append(f"[bold]Rewrite:[/bold] {qu.get('rewritten_query')}")
    if qu.get("entities"):
        lines.append(f"[bold]Entities:[/bold] {', '.join(qu.get('entities', [])[:8])}")
    if qu.get("keywords"):
        lines.append(f"[bold]Keywords:[/bold] {', '.join(qu.get('keywords', [])[:10])}")
    if qu.get("page_start"):
        page_end = qu.get("page_end") or qu.get("page_start")
        lines.append(f"[bold]Page filter:[/bold] {qu.get('page_start')}-{page_end}")
    console.print(Panel("\n".join(lines), title="Query understanding", border_style="magenta"))

def print_answer(result: dict):
    print_query_understanding(result.get("query_understanding", {}))
    answer = result.get("answer") or "Không có câu trả lời."
    console.print(Panel(Markdown(answer), title="Câu trả lời", border_style="green", padding=(1, 2)))
    print_sources(result.get("sources", []))
    print_graph_paths(result.get("graph_paths", []))


def main():
    console.print(
        Panel(
            Text(
                "Math GraphRAG Terminal Chat\n"
                "Hỏi đáp trên dữ liệu sách Toán đã build trong Neo4j.\n\n"
                "Lệnh:\n"
                "- exit / quit / q: thoát\n"
                "- clear: xóa màn hình\n",
                justify="center",
            ),
            title="Domain Knowledge Graph for High School Math",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    try:
        with console.status("[bold green]Đang load GraphRAG system...[/bold green]"):
            retriever = build_retriever()
        console.print("[green]✓ Load hệ thống thành công.[/green]")
        console.print("[dim]Bây giờ anh có thể nhập câu hỏi.[/dim]\n")
    except Exception as e:
        console.print("[red]Không load được hệ thống GraphRAG.[/red]")
        console.print(str(e))
        console.print(traceback.format_exc())
        return

    while True:
        try:
            question = Prompt.ask("[bold cyan]Bạn hỏi[/bold cyan]").strip()
            if not question:
                continue
            if question.lower() in {"exit", "quit", "q"}:
                console.print("[yellow]Đã thoát chat.[/yellow]")
                break
            if question.lower() == "clear":
                console.clear()
                continue

            with console.status("[bold green]Đang truy vấn GraphRAG...[/bold green]"):
                result = retriever.answer(question)

            console.print()
            console.print(Panel(question, title="Câu hỏi", border_style="blue"))
            print_answer(result)
            console.print("\n" + "-" * 100 + "\n")
        except KeyboardInterrupt:
            console.print("\n[yellow]Đã thoát chat.[/yellow]")
            break
        except LLMQuotaError as e:
            console.print("[yellow]Gemini dang het quota hoac bi gioi han toc do.[/yellow]")
            console.print(str(e))
            console.print(
                "[dim]Goi y: cho quota reset, doi GOOGLE_API_KEY, bat billing, "
                "doi model, hoac giam so lan goi LLM trong configs/config.yaml.[/dim]"
            )
        except Exception as e:
            console.print("[red]Có lỗi khi query.[/red]")
            console.print(str(e))
            console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
