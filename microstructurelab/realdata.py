from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    previous_close: float
    last_price: float
    volume: int
    avg_volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None

    @property
    def gap_pct(self) -> float:
        if not self.previous_close:
            return 0.0
        return (self.last_price - self.previous_close) / self.previous_close * 100

    @property
    def relative_volume(self) -> float:
        if not self.avg_volume:
            return 0.0
        return self.volume / self.avg_volume

    @property
    def spread_bps(self) -> Optional[float]:
        if self.bid is None or self.ask is None or self.last_price <= 0:
            return None
        return (self.ask - self.bid) / self.last_price * 10_000


@dataclass(slots=True)
class TextSignal:
    source: str
    symbol: str
    title: str
    url: str = ""
    score: float = 0.0
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ScreenedSymbol:
    symbol: str
    score: float
    market: MarketSnapshot
    news: List[TextSignal]
    community: List[TextSignal]
    risk_flags: List[str]
    rationale: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "market": asdict(self.market),
            "news": [asdict(item) for item in self.news],
            "community": [asdict(item) for item in self.community],
            "risk_flags": self.risk_flags,
            "rationale": self.rationale,
        }


SAMPLE_MARKET = {
    "NVDA": MarketSnapshot("NVDA", 910.0, 949.0, 78_000_000, 42_000_000, 948.9, 949.2, 955.0, 920.0),
    "TSLA": MarketSnapshot("TSLA", 175.0, 183.4, 105_000_000, 88_000_000, 183.3, 183.5, 186.0, 177.0),
    "AMD": MarketSnapshot("AMD", 162.0, 166.5, 62_000_000, 51_000_000, 166.4, 166.55, 168.0, 161.5),
    "AAPL": MarketSnapshot("AAPL", 192.0, 192.8, 44_000_000, 58_000_000, 192.79, 192.81, 193.5, 191.9),
}

SAMPLE_NEWS = {
    "NVDA": [TextSignal("sample-news", "NVDA", "Chip supplier rallies on AI infrastructure demand", score=2.0)],
    "TSLA": [TextSignal("sample-news", "TSLA", "Automaker draws premarket attention after delivery commentary", score=1.4)],
    "AMD": [TextSignal("sample-news", "AMD", "Semiconductor peers move higher in premarket", score=1.1)],
}

SAMPLE_COMMUNITY = {
    "NVDA": [TextSignal("sample-community", "NVDA", "High engagement discussion around AI names", score=2.0, metadata={"comments": 120})],
    "TSLA": [TextSignal("sample-community", "TSLA", "Retail discussion active before open", score=1.7, metadata={"comments": 95})],
    "AMD": [TextSignal("sample-community", "AMD", "Moderate attention in trading forums", score=0.9, metadata={"comments": 40})],
}


def _read_json(url: str, timeout: float = 8.0) -> Dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "MicrostructureLab/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def sample_market(symbol: str) -> MarketSnapshot:
    return SAMPLE_MARKET.get(symbol.upper(), MarketSnapshot(symbol.upper(), 100.0, 100.0, 1_000_000, 1_000_000))


def yahoo_market(symbol: str) -> MarketSnapshot:
    query = urllib.parse.urlencode({"range": "2d", "interval": "5m"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?{query}"
    data = _read_json(url)
    result = data["chart"]["result"][0]
    meta = result["meta"]
    indicators = result.get("indicators", {}).get("quote", [{}])[0]
    closes = [x for x in indicators.get("close", []) if x is not None]
    volumes = [x or 0 for x in indicators.get("volume", [])]
    last_price = float(meta.get("regularMarketPrice") or closes[-1])
    previous_close = float(meta.get("previousClose") or (closes[0] if closes else last_price))
    avg_volume = int(sum(volumes) / len(volumes)) if volumes else 1
    return MarketSnapshot(symbol.upper(), previous_close, last_price, int(sum(volumes[-20:])), avg_volume, meta.get("bid"), meta.get("ask"), meta.get("regularMarketDayHigh"), meta.get("regularMarketDayLow"))


def sample_news(symbol: str) -> List[TextSignal]:
    return SAMPLE_NEWS.get(symbol.upper(), [])


def sample_community(symbol: str) -> List[TextSignal]:
    return SAMPLE_COMMUNITY.get(symbol.upper(), [])


def yahoo_news(symbol: str) -> List[TextSignal]:
    import xml.etree.ElementTree as ET

    url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=" + urllib.parse.quote(symbol.upper())
    request = urllib.request.Request(url, headers={"User-Agent": "MicrostructureLab/1.0"})
    with urllib.request.urlopen(request, timeout=8.0) as response:
        root = ET.fromstring(response.read())
    items: List[TextSignal] = []
    for item in root.findall("./channel/item")[:10]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        items.append(TextSignal("yahoo-news", symbol.upper(), title, link, score=_text_score(title)))
    return items


def gdelt_news(symbol: str) -> List[TextSignal]:
    query = urllib.parse.urlencode({"query": symbol.upper(), "mode": "ArtList", "format": "json", "maxrecords": 10})
    data = _read_json("https://api.gdeltproject.org/api/v2/doc/doc?" + query)
    return [TextSignal("gdelt", symbol.upper(), article.get("title", ""), article.get("url", ""), score=_text_score(article.get("title", ""))) for article in data.get("articles", [])]


def reddit_mentions(symbol: str) -> List[TextSignal]:
    query = urllib.parse.urlencode({"q": symbol.upper(), "sort": "hot", "limit": 10, "restrict_sr": "false"})
    url = "https://www.reddit.com/search.json?" + query
    data = _read_json(url)
    items: List[TextSignal] = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = post.get("title", "")
        comments = int(post.get("num_comments", 0) or 0)
        ups = int(post.get("ups", 0) or 0)
        score = min(3.0, math.log1p(comments + ups) / 2)
        items.append(TextSignal("reddit", symbol.upper(), title, "https://reddit.com" + post.get("permalink", ""), score, {"comments": comments, "ups": ups}))
    return items


def _text_score(text: str) -> float:
    text = text.lower()
    positives = ["beat", "surge", "rally", "upgrade", "record", "growth", "ai", "strong"]
    negatives = ["miss", "probe", "lawsuit", "downgrade", "weak", "falls", "warning"]
    return sum(word in text for word in positives) - sum(word in text for word in negatives)


def screen_open(symbols: Iterable[str], market_provider: str = "sample", news_provider: str = "sample", community_provider: str = "sample") -> List[ScreenedSymbol]:
    results: List[ScreenedSymbol] = []
    for raw in symbols:
        symbol = raw.strip().upper()
        if not symbol:
            continue
        market = yahoo_market(symbol) if market_provider == "yahoo" else sample_market(symbol)
        news = yahoo_news(symbol) if news_provider == "yahoo" else gdelt_news(symbol) if news_provider == "gdelt" else sample_news(symbol)
        community = reddit_mentions(symbol) if community_provider == "reddit" else sample_community(symbol)
        risk_flags: List[str] = []
        rationale: List[str] = []
        score = 0.0
        score += min(4.0, abs(market.gap_pct) * 0.7)
        score += min(3.0, market.relative_volume)
        score += min(2.0, sum(item.score for item in news))
        score += min(2.0, sum(item.score for item in community))
        if market.volume < 500_000:
            risk_flags.append("low_liquidity")
            score -= 1.5
        if market.spread_bps is not None and market.spread_bps > 20:
            risk_flags.append("wide_spread")
            score -= 1.0
        if abs(market.gap_pct) < 1.0:
            risk_flags.append("small_gap")
        if not news:
            risk_flags.append("no_news_catalyst")
        if not community:
            risk_flags.append("low_community_visibility")
        if abs(market.gap_pct) > 12:
            risk_flags.append("extreme_gap_risk")
        rationale.append(f"gap={market.gap_pct:.2f}%")
        rationale.append(f"relative_volume={market.relative_volume:.2f}x")
        rationale.append(f"news_items={len(news)}")
        rationale.append(f"community_items={len(community)}")
        results.append(ScreenedSymbol(symbol, round(score, 3), market, news, community, risk_flags, rationale))
    return sorted(results, key=lambda item: item.score, reverse=True)
