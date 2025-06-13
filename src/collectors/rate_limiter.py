"""
API レート制限管理モジュール

各種外部APIのレート制限を管理し、適切な間隔でのリクエスト実行を制御します。
Steam Web API以外のAPIでも再利用可能な汎用的な実装を提供します。
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """レート制限戦略の種類"""
    SLIDING_WINDOW = "sliding_window"  # スライディングウィンドウ方式
    FIXED_WINDOW = "fixed_window"      # 固定ウィンドウ方式
    TOKEN_BUCKET = "token_bucket"      # トークンバケット方式


@dataclass
class RateLimitConfig:
    """レート制限設定"""
    max_requests: int = 100              # 最大リクエスト数
    time_window: int = 60                # 時間ウィンドウ（秒）
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_size: Optional[int] = None     # バースト許可サイズ（トークンバケット用）
    backoff_factor: float = 1.5          # バックオフ係数
    max_backoff_time: float = 300.0      # 最大バックオフ時間（秒）
    
    def __post_init__(self):
        """設定値の検証"""
        if self.max_requests <= 0:
            raise ValueError("max_requests は正の整数である必要があります")
        if self.time_window <= 0:
            raise ValueError("time_window は正の整数である必要があります")
        if self.burst_size is None:
            self.burst_size = self.max_requests


@dataclass
class RequestRecord:
    """リクエスト記録"""
    timestamp: datetime
    success: bool = True
    response_time: Optional[float] = None
    error_message: Optional[str] = None


class SlidingWindowRateLimiter:
    """スライディングウィンドウ方式のレート制限実装
    
    過去N秒間のリクエスト数を常に監視し、制限を超えないよう制御します。
    最も正確な制限管理が可能ですが、メモリ使用量が多くなる可能性があります。
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: List[RequestRecord] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self, weight: int = 1) -> float:
        """リクエスト許可を取得
        
        Args:
            weight: リクエストの重み（デフォルト: 1）
            
        Returns:
            待機時間（秒）
        """
        async with self._lock:
            now = datetime.now()
            
            # 古いリクエスト記録を削除
            cutoff_time = now - timedelta(seconds=self.config.time_window)
            self.requests = [req for req in self.requests if req.timestamp > cutoff_time]
            
            # 現在のリクエスト数をチェック
            current_requests = sum(1 for req in self.requests if req.success)
            
            if current_requests + weight > self.config.max_requests:
                # 最も古いリクエストが期限切れになるまでの時間を計算
                if self.requests:
                    oldest_request = min(self.requests, key=lambda r: r.timestamp)
                    wait_time = (oldest_request.timestamp + timedelta(seconds=self.config.time_window) - now).total_seconds()
                    wait_time = max(0, wait_time)
                else:
                    wait_time = self.config.time_window
                
                logger.debug(f"レート制限により {wait_time:.2f}秒待機します")
                return wait_time
            
            # リクエスト記録を追加
            self.requests.append(RequestRecord(timestamp=now))
            return 0.0
    
    def record_response(self, success: bool, response_time: Optional[float] = None, error_message: Optional[str] = None):
        """レスポンス結果を記録
        
        Args:
            success: リクエストが成功したか
            response_time: レスポンス時間（秒）
            error_message: エラーメッセージ（失敗時）
        """
        if self.requests:
            self.requests[-1].success = success
            self.requests[-1].response_time = response_time
            self.requests[-1].error_message = error_message
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得
        
        Returns:
            レート制限の統計情報
        """
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.config.time_window)
        recent_requests = [req for req in self.requests if req.timestamp > cutoff_time]
        
        successful_requests = [req for req in recent_requests if req.success]
        failed_requests = [req for req in recent_requests if not req.success]
        
        response_times = [req.response_time for req in recent_requests if req.response_time is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_requests": len(recent_requests),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(recent_requests) if recent_requests else 0,
            "average_response_time": avg_response_time,
            "current_capacity": self.config.max_requests - len(successful_requests),
            "time_window": self.config.time_window,
        }


class TokenBucketRateLimiter:
    """トークンバケット方式のレート制限実装
    
    一定間隔でトークンを補充し、リクエスト時にトークンを消費します。
    バースト対応が優秀で、メモリ効率も良い実装です。
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_size)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        
        # トークン補充レート（秒あたり）
        self.refill_rate = config.max_requests / config.time_window
    
    async def acquire(self, weight: int = 1) -> float:
        """トークンを取得
        
        Args:
            weight: 必要なトークン数
            
        Returns:
            待機時間（秒）
        """
        async with self._lock:
            now = time.time()
            
            # トークンを補充
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.config.burst_size, self.tokens + tokens_to_add)
            self.last_refill = now
            
            # トークンが不足している場合
            if self.tokens < weight:
                tokens_needed = weight - self.tokens
                wait_time = tokens_needed / self.refill_rate
                logger.debug(f"トークン不足により {wait_time:.2f}秒待機します")
                return wait_time
            
            # トークンを消費
            self.tokens -= weight
            return 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "available_tokens": self.tokens,
            "max_tokens": self.config.burst_size,
            "refill_rate": self.refill_rate,
            "utilization": 1.0 - (self.tokens / self.config.burst_size),
        }


class AdaptiveRateLimiter:
    """適応的レート制限器
    
    APIの応答時間やエラー率に基づいて、動的にレート制限を調整します。
    実際のAPI性能に合わせた最適なスループットを実現します。
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.base_limiter = SlidingWindowRateLimiter(config)
        
        # 適応制御パラメータ
        self.current_limit = config.max_requests
        self.min_limit = max(1, config.max_requests // 10)
        self.max_limit = config.max_requests * 2
        
        # 性能監視
        self.recent_errors = []
        self.recent_response_times = []
        self.adjustment_history = []
        
        # 調整閾値
        self.error_threshold = 0.1      # エラー率10%超過で制限強化
        self.response_time_threshold = 5.0  # 5秒超過で制限強化
        self.adjustment_interval = 60   # 60秒間隔で調整判定
        self.last_adjustment = time.time()
    
    async def acquire(self, weight: int = 1) -> float:
        """適応的レート制限でリクエスト取得
        
        Args:
            weight: リクエストの重み
            
        Returns:
            待機時間（秒）
        """
        # 定期的に制限値を調整
        await self._adjust_limits()
        
        # 現在の制限値でリクエスト取得
        return await self.base_limiter.acquire(weight)
    
    async def _adjust_limits(self):
        """制限値の動的調整"""
        now = time.time()
        if now - self.last_adjustment < self.adjustment_interval:
            return
        
        # 最近の性能データを分析
        recent_cutoff = now - self.adjustment_interval
        recent_errors = [err for err in self.recent_errors if err > recent_cutoff]
        recent_times = [rt for rt in self.recent_response_times if rt[0] > recent_cutoff]
        
        error_rate = len(recent_errors) / max(1, len(self.base_limiter.requests))
        avg_response_time = sum(rt[1] for rt in recent_times) / max(1, len(recent_times))
        
        old_limit = self.current_limit
        
        # 制限値の調整ロジック
        if error_rate > self.error_threshold or avg_response_time > self.response_time_threshold:
            # 性能悪化 → 制限を強化（リクエスト数減少）
            self.current_limit = max(self.min_limit, int(self.current_limit * 0.8))
            adjustment_reason = f"エラー率: {error_rate:.3f}, 応答時間: {avg_response_time:.2f}s"
        elif error_rate < self.error_threshold / 2 and avg_response_time < self.response_time_threshold / 2:
            # 性能良好 → 制限を緩和（リクエスト数増加）
            self.current_limit = min(self.max_limit, int(self.current_limit * 1.1))
            adjustment_reason = "性能良好"
        else:
            adjustment_reason = "調整不要"
        
        # 制限値の更新
        if old_limit != self.current_limit:
            self.base_limiter.config.max_requests = self.current_limit
            self.adjustment_history.append({
                "timestamp": now,
                "old_limit": old_limit,
                "new_limit": self.current_limit,
                "reason": adjustment_reason,
                "error_rate": error_rate,
                "avg_response_time": avg_response_time,
            })
            
            logger.info(f"レート制限を調整: {old_limit} → {self.current_limit} ({adjustment_reason})")
        
        self.last_adjustment = now
    
    def record_response(self, success: bool, response_time: Optional[float] = None, error_message: Optional[str] = None):
        """レスポンス結果を記録（適応制御用）"""
        now = time.time()
        
        # ベースリミッターにも記録
        self.base_limiter.record_response(success, response_time, error_message)
        
        # 適応制御用データを記録
        if not success:
            self.recent_errors.append(now)
        
        if response_time is not None:
            self.recent_response_times.append((now, response_time))
        
        # 古いデータを削除（メモリ効率化）
        cutoff_time = now - self.adjustment_interval * 2
        self.recent_errors = [err for err in self.recent_errors if err > cutoff_time]
        self.recent_response_times = [rt for rt in self.recent_response_times if rt[0] > cutoff_time]
    
    def get_statistics(self) -> Dict[str, Any]:
        """詳細統計情報を取得"""
        base_stats = self.base_limiter.get_statistics()
        
        return {
            **base_stats,
            "adaptive_limit": self.current_limit,
            "base_limit": self.config.max_requests,
            "adjustment_count": len(self.adjustment_history),
            "recent_adjustments": self.adjustment_history[-5:],  # 最新5件
            "error_count": len(self.recent_errors),
            "avg_response_time_samples": len(self.recent_response_times),
        }


def create_rate_limiter(config: RateLimitConfig) -> Any:
    """設定に基づいてレート制限器を作成
    
    Args:
        config: レート制限設定
        
    Returns:
        設定に応じたレート制限器インスタンス
    """
    if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
        return SlidingWindowRateLimiter(config)
    elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
        return TokenBucketRateLimiter(config)
    else:
        raise ValueError(f"未サポートの戦略: {config.strategy}")


# 便利な設定プリセット
class RateLimitPresets:
    """よく使用されるレート制限設定のプリセット"""
    
    @staticmethod
    def steam_api() -> RateLimitConfig:
        """Steam Web API 用設定（200req/5min）"""
        return RateLimitConfig(
            max_requests=200,
            time_window=300,  # 5分
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            backoff_factor=2.0,
            max_backoff_time=600.0,
        )
    
    @staticmethod
    def twitter_api() -> RateLimitConfig:
        """Twitter API 用設定（300req/15min）"""
        return RateLimitConfig(
            max_requests=300,
            time_window=900,  # 15分
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
    
    @staticmethod
    def github_api() -> RateLimitConfig:
        """GitHub API 用設定（5000req/hour）"""
        return RateLimitConfig(
            max_requests=5000,
            time_window=3600,  # 1時間
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_size=100,
        )
    
    @staticmethod
    def conservative() -> RateLimitConfig:
        """保守的な設定（10req/min）"""
        return RateLimitConfig(
            max_requests=10,
            time_window=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )


# 使用例とテスト
async def test_rate_limiters():
    """レート制限器のテスト"""
    
    print("🚦 レート制限器テスト開始...")
    
    # スライディングウィンドウ方式のテスト
    print("\n📊 スライディングウィンドウ方式テスト")
    config = RateLimitConfig(max_requests=5, time_window=10)
    limiter = SlidingWindowRateLimiter(config)
    
    start_time = time.time()
    for i in range(8):  # 制限を超える数のリクエスト
        wait_time = await limiter.acquire()
        if wait_time > 0:
            print(f"   リクエスト {i+1}: {wait_time:.2f}秒待機")
            await asyncio.sleep(wait_time)
        else:
            print(f"   リクエスト {i+1}: 即座に実行")
        
        # 成功をシミュレート
        limiter.record_response(True, response_time=0.5)
    
    total_time = time.time() - start_time
    print(f"   総実行時間: {total_time:.2f}秒")
    print(f"   統計: {limiter.get_statistics()}")
    
    # トークンバケット方式のテスト
    print("\n🪣 トークンバケット方式テスト")
    token_config = RateLimitConfig(
        max_requests=10, 
        time_window=10,
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        burst_size=5
    )
    token_limiter = TokenBucketRateLimiter(token_config)
    
    # バーストリクエストのテスト
    print("   バーストリクエスト（5件連続）:")
    for i in range(5):
        wait_time = await token_limiter.acquire()
        print(f"     リクエスト {i+1}: {wait_time:.2f}秒待機")
    
    print(f"   統計: {token_limiter.get_statistics()}")
    
    print("\n✅ レート制限器テスト完了!")


if __name__ == "__main__":
    asyncio.run(test_rate_limiters())