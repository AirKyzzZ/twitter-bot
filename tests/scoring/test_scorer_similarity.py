"""Tests for content scorer similarity checks."""

from twitter_bot.scoring.scorer import ContentScorer

def test_select_best_skips_similar_titles():
    """Test that select_best skips items with titles similar to recent ones."""
    scorer = ContentScorer()
    
    items = [
        ("New Vercel AI Gateway Features", "http://example.com/1", "content", 1.0),
        ("Unrelated News", "http://example.com/2", "content", 1.0),
    ]
    
    # "New Vercel AI Gateway Features" is very similar to "Vercel AI Gateway Features Released"
    recent_titles = ["Vercel AI Gateway Features Released"]
    
    best = scorer.select_best(items, recent_titles=recent_titles)
    
    assert best is not None
    assert best.title == "Unrelated News"
    assert best.url == "http://example.com/2"

def test_select_best_allows_dissimilar_titles():
    """Test that select_best allows items that are not similar."""
    scorer = ContentScorer()
    
    items = [
        ("New Vercel AI Gateway Features", "http://example.com/1", "content", 1.0),
    ]
    
    recent_titles = ["Something completely different"]
    
    best = scorer.select_best(items, recent_titles=recent_titles)
    
    assert best is not None
    assert best.title == "New Vercel AI Gateway Features"

def test_select_best_handles_empty_recent_titles():
    """Test that select_best works with no recent titles."""
    scorer = ContentScorer()
    
    items = [
        ("Title 1", "http://url1", "content", 1.0),
    ]
    
    best = scorer.select_best(items, recent_titles=[])
    
    assert best is not None
    assert best.title == "Title 1"
