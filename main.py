import asyncio
import io
import csv
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from scraper import scrape_comments, InstagramError
from raffle import run_raffle

app = FastAPI(title="Instagram Comments Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=2)

_comments_store: list[dict] = []


class ScrapeRequest(BaseModel):
    url: str
    username: str = ""
    password: str = ""


class RaffleRequest(BaseModel):
    mention_filter: Optional[str] = None
    exclude_duplicates: bool = True
    num_winners: int = 1


@app.post("/api/scrape")
async def scrape(req: ScrapeRequest):
    global _comments_store
    loop = asyncio.get_event_loop()
    try:
        comments = await loop.run_in_executor(
            executor,
            lambda: scrape_comments(req.url, req.username, req.password),
        )
    except InstagramError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

    _comments_store = comments
    return {"comments": comments, "total": len(comments)}


@app.get("/api/export/csv")
async def export_csv():
    if not _comments_store:
        raise HTTPException(status_code=400, detail="No hay comentarios cargados")

    output = io.StringIO()
    fieldnames = ["username", "text", "created_at", "mentions", "likes"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(_comments_store)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="comentarios.csv"'},
    )


@app.post("/api/raffle")
async def raffle(req: RaffleRequest):
    if not _comments_store:
        raise HTTPException(status_code=400, detail="No hay comentarios cargados")

    winners = run_raffle(
        _comments_store,
        mention_filter=req.mention_filter,
        exclude_duplicates=req.exclude_duplicates,
        num_winners=req.num_winners,
    )
    return {"winners": winners, "pool_size": len(_comments_store)}


@app.get("/api/status")
async def status():
    return {"loaded": len(_comments_store), "ready": len(_comments_store) > 0}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
