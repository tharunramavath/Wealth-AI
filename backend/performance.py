"""
Performance Optimization Module
- Async parallel stock fetching
- Memory caching with TTL
- Batch processing
- Progress streaming
"""

import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import warnings
warnings.filterwarnings('ignore')


class MemoryCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 900):
        self._cache = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry["expires_at"] > time.time():
                    return entry["value"]
                else:
                    del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + (ttl or self.default_ttl),
                "created_at": time.time()
            }
    
    def delete(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        with self._lock:
            return len(self._cache)
    
    def cleanup(self):
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._cache.items() if v["expires_at"] <= now]
            for k in expired:
                del self._cache[k]
            return len(expired)


cache = MemoryCache(default_ttl=900)


class AsyncStockFetcher:
    """Fetch stock data asynchronously in parallel."""
    
    def __init__(self, max_concurrent: int = 10, timeout: int = 15):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = None
    
    async def fetch_single(self, ticker: str, start_date: datetime, end_date: datetime) -> Dict:
        """Fetch data for a single ticker."""
        cache_key = f"{ticker}_{start_date.date()}_{end_date.date()}"
        
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(
                None,
                lambda: yf.Ticker(ticker).history(start=start_date, end=end_date, timeout=self.timeout)
            )
            
            if hist is not None and not hist.empty and 'Close' in hist.columns:
                closes = hist['Close'].dropna()
                result = {
                    "ticker": ticker,
                    "success": True,
                    "prices": closes.tolist(),
                    "dates": [str(d.date()) for d in closes.index],
                    "current_price": float(closes.iloc[-1]),
                    "start_price": float(closes.iloc[0]),
                    "return": float((closes.iloc[-1] / closes.iloc[0] - 1) * 100),
                    "high": float(closes.max()),
                    "low": float(closes.min()),
                    "volume_avg": float(hist['Volume'].mean()) if 'Volume' in hist.columns else 0,
                    "fetched_at": datetime.now().isoformat()
                }
                cache.set(cache_key, result, ttl=900)
                return result
            else:
                return {"ticker": ticker, "success": False, "error": "No data available"}
                
        except Exception as e:
            return {"ticker": ticker, "success": False, "error": str(e)}
    
    async def fetch_multiple(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """Fetch data for multiple tickers in parallel."""
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(ticker):
            async with self.semaphore:
                result = await self.fetch_single(ticker, start_date, end_date)
                if progress_callback:
                    await progress_callback(ticker, result["success"])
                return result
        
        tasks = [fetch_with_semaphore(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed = []
        for r in results:
            if isinstance(r, Exception):
                processed.append({"ticker": "unknown", "success": False, "error": str(r)})
            else:
                processed.append(r)
        
        return processed
    
    def fetch_multiple_sync(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable[[str, bool], None]] = None
    ) -> List[Dict]:
        """Synchronous wrapper for fetch_multiple."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.fetch_multiple(tickers, start_date, end_date, progress_callback)
            )
        finally:
            loop.close()


class BatchProcessor:
    """Process data in batches for better performance."""
    
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
    
    def process_in_batches(
        self,
        items: List[Any],
        processor: Callable,
        on_batch_complete: Optional[Callable] = None
    ) -> List[Any]:
        """Process items in batches."""
        results = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = []
            
            with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
                futures = {executor.submit(processor, item): item for item in batch}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        batch_results.append({"error": str(e)})
            
            results.extend(batch_results)
            
            if on_batch_complete:
                current_batch = i // self.batch_size + 1
                on_batch_complete(current_batch, total_batches, len(batch_results))
        
        return results


class ProgressTracker:
    """Track progress for long-running operations."""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.success = 0
        self.failed = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
        self.callbacks = []
    
    def increment(self, success: bool = True):
        with self._lock:
            self.completed += 1
            if success:
                self.success += 1
            else:
                self.failed += 1
            self._notify()
    
    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)
    
    def _notify(self):
        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed if elapsed > 0 else 0
        eta = (self.total - self.completed) / rate if rate > 0 else 0
        
        status = {
            "completed": self.completed,
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "progress_pct": round(self.completed / self.total * 100, 1) if self.total > 0 else 0,
            "elapsed_seconds": round(elapsed, 1),
            "eta_seconds": round(eta, 1),
            "rate_per_second": round(rate, 1)
        }
        
        for cb in self.callbacks:
            try:
                cb(status)
            except:
                pass
    
    def get_status(self) -> Dict:
        with self._lock:
            elapsed = time.time() - self.start_time
            rate = self.completed / elapsed if elapsed > 0 else 0
            return {
                "completed": self.completed,
                "total": self.total,
                "success": self.success,
                "failed": self.failed,
                "progress_pct": round(self.completed / self.total * 100, 1) if self.total > 0 else 0,
                "elapsed_seconds": round(elapsed, 1),
                "rate_per_second": round(rate, 1)
            }


async def stream_results_async(items: List[Any], processor: Callable) -> Dict:
    """Stream results as they complete."""
    queue = asyncio.Queue()
    completed = []
    total = len(items)
    
    async def producer():
        for item in items:
            await queue.put(item)
    
    async def consumer():
        while len(completed) < total:
            item = await queue.get()
            try:
                result = await processor(item)
                completed.append({"item": item, "result": result, "success": True})
            except Exception as e:
                completed.append({"item": item, "result": str(e), "success": False})
            queue.task_done()
    
    producers = [asyncio.create_task(producer()) for _ in range(1)]
    consumers = [asyncio.create_task(consumer()) for _ in range(10)]
    
    await asyncio.gather(*producers)
    await queue.join()
    await asyncio.gather(*consumers, return_exceptions=True)
    
    return {
        "total": total,
        "completed": len(completed),
        "success": sum(1 for c in completed if c["success"]),
        "failed": sum(1 for c in completed if not c["success"]),
        "results": completed
    }


def benchmark_fetch(tickers: List[str], days: int = 90) -> Dict:
    """Benchmark fetch performance."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    
    fetcher = AsyncStockFetcher(max_concurrent=10)
    
    start = time.time()
    results = fetcher.fetch_multiple_sync(tickers, start_date, end_date)
    parallel_time = time.time() - start
    
    start_seq = time.time()
    for t in tickers:
        try:
            yf.Ticker(t).history(start=start_date, end=end_date)
        except:
            pass
    sequential_time = time.time() - start_seq
    
    return {
        "tickers": len(tickers),
        "parallel_time_seconds": round(parallel_time, 2),
        "sequential_time_seconds": round(sequential_time, 2),
        "speedup": round(sequential_time / parallel_time, 2) if parallel_time > 0 else 0,
        "success_count": sum(1 for r in results if r.get("success", False)),
        "cache_size": cache.size()
    }


cache_cleanup_thread = None
_cache_running = False

def start_cache_cleanup(interval: int = 300):
    """Start background cache cleanup thread."""
    global _cache_running
    _cache_running = True
    
    def cleanup_loop():
        while _cache_running:
            time.sleep(interval)
            deleted = cache.cleanup()
            if deleted > 0:
                print(f"Cache cleanup: removed {deleted} expired entries")
    
    import threading
    global cache_cleanup_thread
    cache_cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cache_cleanup_thread.start()

def stop_cache_cleanup():
    global _cache_running
    _cache_running = False
