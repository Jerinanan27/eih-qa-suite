import re
import pytest
from playwright.sync_api import Page, expect

GEN_TIMEOUT = 120_000  # ms — generous for cold-start + RAG generation


def _wake_and_wait(page: Page):
    """Wake the Community Cloud sleep screen if present, then wait for the app to boot.
    On a local instance there's no sleep screen, so the wake step is skipped."""
    wake = page.get_by_role("button", name=re.compile("get this app back up", re.I))
    try:
        wake.wait_for(timeout=8000)
        wake.click()
    except Exception:
        pass
    expect(
        page.get_by_role("heading", name=re.compile("Engineering Intelligence Hub", re.I))
    ).to_be_visible(timeout=GEN_TIMEOUT)


def test_home_loads(page: Page, ui_url):
    page.goto(ui_url, timeout=GEN_TIMEOUT)
    _wake_and_wait(page)


def test_ask_returns_answer_and_citations(page: Page, ui_url):
    page.goto(ui_url, timeout=GEN_TIMEOUT)
    _wake_and_wait(page)

    box = page.get_by_placeholder(re.compile("token validation", re.I))
    expect(box).to_be_visible(timeout=GEN_TIMEOUT)
    box.fill("How are JWTs validated, and what broke in INC-2025-014?")
    box.press("Enter")

    # exact=True so "Answer"/"Sources" don't also match the sidebar's "Filter sources".
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=GEN_TIMEOUT)
    expect(page.get_by_role("heading", name="Sources", exact=True)).to_be_visible(timeout=GEN_TIMEOUT)
    expect(page.get_by_text(re.compile(r"\[1\].*score", re.S)).first).to_be_visible(timeout=GEN_TIMEOUT)


def test_empty_question_shows_no_answer(page: Page, ui_url):
    page.goto(ui_url, timeout=GEN_TIMEOUT)
    _wake_and_wait(page)
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_have_count(0)
