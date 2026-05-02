import re
from datetime import timezone
from typing import Optional

try:
    import instaloader
except ImportError as exc:
    raise ImportError("Install instaloader: pip install instaloader") from exc


class InstagramError(Exception):
    pass


def _extract_shortcode(url: str) -> str:
    patterns = [
        r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)",
        r"instagr\.am/p/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise InstagramError(f"No se pudo extraer el shortcode de la URL: {url}")


def _extract_mentions(text: str) -> list[str]:
    return re.findall(r"@([A-Za-z0-9_.]+)", text)


def scrape_comments(url: str, username: str = "", password: str = "") -> list[dict]:
    shortcode = _extract_shortcode(url)
    loader = instaloader.Instaloader(
        download_pictures=False, download_videos=False,
        download_video_thumbnails=False, download_geotags=False,
        download_comments=False, save_metadata=False,
        compress_json=False, quiet=True,
    )
    if username and password:
        try:
            loader.login(username, password)
        except instaloader.exceptions.BadCredentialsException:
            raise InstagramError("Credenciales de Instagram incorrectas.")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            raise InstagramError("La cuenta requiere autenticación de dos factores.")
        except instaloader.exceptions.ConnectionException as e:
            raise InstagramError(f"Error de conexión al iniciar sesión: {e}")
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
    except instaloader.exceptions.LoginRequiredException:
        raise InstagramError("Este post requiere iniciar sesión en Instagram.")
    except instaloader.exceptions.PrivateProfileNotFollowedException:
        raise InstagramError("El perfil es privado y no lo seguís con la cuenta ingresada.")
    except instaloader.exceptions.ConnectionException as e:
        raise InstagramError(f"Error de conexión: {e}")
    except Exception as e:
        raise InstagramError(f"No se pudo obtener el post: {e}")
    comments: list[dict] = []
    try:
        for comment in post.get_comments():
            text = comment.text or ""
            created_at = comment.created_at_utc.replace(tzinfo=timezone.utc).isoformat() if comment.created_at_utc else None
            comments.append({"username": comment.owner.username, "text": text, "created_at": created_at, "mentions": _extract_mentions(text), "likes": getattr(comment, "likes_count", 0)})
            for reply in comment.answers:
                rt = reply.text or ""
                rca = reply.created_at_utc.replace(tzinfo=timezone.utc).isoformat() if reply.created_at_utc else None
                comments.append({"username": reply.owner.username, "text": rt, "created_at": rca, "mentions": _extract_mentions(rt), "likes": getattr(reply, "likes_count", 0)})
    except instaloader.exceptions.LoginRequiredException:
        raise InstagramError("Se necesita iniciar sesión para obtener los comentarios.")
    except instaloader.exceptions.ConnectionException as e:
        raise InstagramError(f"Error de conexión al obtener comentarios: {e}")
    except Exception as e:
        raise InstagramError(f"Error al leer comentarios: {e}")
    return comments
