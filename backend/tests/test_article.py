import pytest
from unittest.mock import patch, MagicMock
from app.services.article import fetch_rss_candidates, extract_article_text

def test_fetch_rss_returns_entries():
    mock_feed = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "AI Breakthrough"
    mock_entry.link = "https://example.com/article1"
    mock_entry.get = lambda k, d=None: {"published": "2026-04-01"}.get(k, d)
    mock_feed.entries = [mock_entry]
    mock_feed.feed = MagicMock()
    mock_feed.feed.get = lambda k, d=None: {"title": "TechCrunch"}.get(k, d)
    with patch("app.services.article.feedparser.parse", return_value=mock_feed):
        results = fetch_rss_candidates("https://feeds.example.com/rss")
        assert len(results) == 1
        assert results[0]["title"] == "AI Breakthrough"
        assert results[0]["type"] == "article"

def test_extract_article_text_returns_content():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<html><body><p>Article content here.</p></body></html>"
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        with patch("app.services.article.trafilatura.extract", return_value="Article content here."):
            text = extract_article_text("https://example.com/article1")
            assert text == "Article content here."

def test_extract_article_text_returns_none_on_failure():
    with patch("urllib.request.urlopen", side_effect=Exception("Connection failed")):
        text = extract_article_text("https://example.com/bad")
        assert text is None
