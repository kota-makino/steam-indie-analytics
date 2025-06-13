"""
Steam API データ検証モジュール

取得したデータの品質チェック、バリデーション、異常値検出を行います。
データパイプラインの信頼性向上とデータ品質管理を目的としています。
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
import logging

from pydantic import BaseModel, validator, Field
from pydantic.types import PositiveInt, conint, confloat

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """検証結果の重要度"""
    INFO = "info"           # 情報レベル
    WARNING = "warning"     # 警告レベル
    ERROR = "error"         # エラーレベル
    CRITICAL = "critical"   # クリティカルレベル


@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""
    field_name: str
    severity: ValidationSeverity
    message: str
    original_value: Any = None
    suggested_value: Any = None
    validation_rule: str = ""


class SteamGameValidator(BaseModel):
    """Steam ゲームデータの Pydantic バリデーションモデル
    
    Steam API から取得したゲームデータの型安全性と
    ビジネスルールの検証を行います。
    """
    
    # 基本情報（必須フィールド）
    app_id: PositiveInt = Field(..., description="Steam アプリケーションID")
    name: str = Field(..., min_length=1, max_length=500, description="ゲーム名")
    type: str = Field(..., description="アプリケーションタイプ")
    
    # フラグ情報
    is_free: bool = Field(default=False, description="無料ゲームフラグ")
    
    # テキスト情報（オプション）
    detailed_description: Optional[str] = Field(None, max_length=50000, description="詳細説明")
    short_description: Optional[str] = Field(None, max_length=1000, description="短い説明")
    
    # 開発・販売者情報
    developers: Optional[List[str]] = Field(None, description="開発者リスト")
    publishers: Optional[List[str]] = Field(None, description="パブリッシャーリスト")
    
    # 価格情報
    price_overview: Optional[Dict[str, Any]] = Field(None, description="価格情報")
    
    # リリース日情報
    release_date: Optional[Dict[str, Any]] = Field(None, description="リリース日情報")
    
    # プラットフォーム情報
    platforms: Optional[Dict[str, bool]] = Field(None, description="対応プラットフォーム")
    
    # ゲーム分類情報
    categories: Optional[List[Dict[str, Any]]] = Field(None, description="カテゴリリスト")
    genres: Optional[List[Dict[str, Any]]] = Field(None, description="ジャンルリスト")
    tags: Optional[List[str]] = Field(None, description="タグリスト")
    
    # レビュー情報
    positive_reviews: Optional[conint(ge=0)] = Field(None, description="肯定的レビュー数")
    negative_reviews: Optional[conint(ge=0)] = Field(None, description="否定的レビュー数")
    total_reviews: Optional[conint(ge=0)] = Field(None, description="総レビュー数")
    recommendation_score: Optional[confloat(ge=0.0, le=100.0)] = Field(None, description="推奨スコア")
    
    @validator('name')
    def validate_name(cls, v):
        """ゲーム名の検証"""
        if not v or v.strip() == "":
            raise ValueError("ゲーム名は空にできません")
        
        # 特殊文字の過度な使用をチェック
        special_char_ratio = sum(1 for c in v if not c.isalnum() and not c.isspace()) / len(v)
        if special_char_ratio > 0.5:
            logger.warning(f"ゲーム名に特殊文字が多すぎます: {v}")
        
        return v.strip()
    
    @validator('type')
    def validate_type(cls, v):
        """アプリケーションタイプの検証"""
        valid_types = ["game", "dlc", "demo", "advertising", "mod", "video", "software"]
        if v.lower() not in valid_types:
            logger.warning(f"未知のアプリケーションタイプ: {v}")
        return v.lower()
    
    @validator('developers', 'publishers')
    def validate_developer_publisher_lists(cls, v):
        """開発者・パブリッシャーリストの検証"""
        if v is None:
            return None
        
        # 空のリストまたは空文字列を含むリストをチェック
        cleaned_list = [item.strip() for item in v if item and item.strip()]
        if len(cleaned_list) != len(v):
            logger.warning("開発者/パブリッシャーリストに空の項目があります")
        
        return cleaned_list if cleaned_list else None
    
    @validator('price_overview')
    def validate_price_overview(cls, v):
        """価格情報の検証"""
        if v is None:
            return None
        
        required_fields = ['currency', 'initial', 'final']
        missing_fields = [field for field in required_fields if field not in v]
        
        if missing_fields:
            logger.warning(f"価格情報に必須フィールドが不足: {missing_fields}")
        
        # 価格の妥当性チェック
        if 'initial' in v and 'final' in v:
            try:
                initial_price = int(v['initial'])
                final_price = int(v['final'])
                
                if initial_price < 0 or final_price < 0:
                    logger.warning("価格に負の値が含まれています")
                
                if final_price > initial_price:
                    logger.warning("最終価格が初期価格を上回っています")
                    
            except (ValueError, TypeError):
                logger.warning("価格情報の形式が無効です")
        
        return v
    
    @validator('release_date')
    def validate_release_date(cls, v):
        """リリース日情報の検証"""
        if v is None:
            return None
        
        if 'date' in v and v['date']:
            # 日付形式の検証
            date_str = v['date']
            date_patterns = [
                r'\d{1,2} \w{3}, \d{4}',  # "1 Jan, 2020"
                r'\w{3} \d{1,2}, \d{4}',  # "Jan 1, 2020"
                r'\d{4}-\d{2}-\d{2}',     # "2020-01-01"
                r'\d{1,2}/\d{1,2}/\d{4}', # "1/1/2020"
            ]
            
            if not any(re.match(pattern, date_str) for pattern in date_patterns):
                logger.warning(f"日付形式が認識できません: {date_str}")
        
        return v
    
    @validator('total_reviews')
    def validate_total_reviews(cls, v, values):
        """総レビュー数の整合性検証"""
        if v is None:
            return None
        
        positive = values.get('positive_reviews', 0) or 0
        negative = values.get('negative_reviews', 0) or 0
        calculated_total = positive + negative
        
        # 許容誤差（5%）以内での不一致は警告レベル
        if calculated_total > 0:
            difference_ratio = abs(v - calculated_total) / calculated_total
            if difference_ratio > 0.05:
                logger.warning(
                    f"レビュー数の不整合: 総数={v}, 計算値={calculated_total}"
                )
        
        return v


class DataQualityAnalyzer:
    """データ品質分析器
    
    Steam API データの品質を多角的に分析し、
    データクリーニングの指針を提供します。
    """
    
    def __init__(self):
        self.validation_results: List[ValidationResult] = []
        self.statistics: Dict[str, Any] = {}
    
    def analyze_game_data(self, game_data: Dict[str, Any]) -> List[ValidationResult]:
        """ゲームデータの品質分析
        
        Args:
            game_data: 分析対象のゲームデータ
            
        Returns:
            検証結果のリスト
        """
        self.validation_results.clear()
        
        # Pydantic バリデーション
        try:
            validated_data = SteamGameValidator(**game_data)
            self._add_result("overall", ValidationSeverity.INFO, "Pydantic バリデーション成功")
        except Exception as e:
            self._add_result("overall", ValidationSeverity.ERROR, f"Pydantic バリデーション失敗: {str(e)}")
        
        # カスタム品質チェック
        self._check_completeness(game_data)
        self._check_consistency(game_data)
        self._check_business_rules(game_data)
        self._check_data_anomalies(game_data)
        
        return self.validation_results
    
    def _add_result(self, field: str, severity: ValidationSeverity, message: str, 
                   original_value: Any = None, suggested_value: Any = None, rule: str = ""):
        """検証結果を追加"""
        result = ValidationResult(
            field_name=field,
            severity=severity,
            message=message,
            original_value=original_value,
            suggested_value=suggested_value,
            validation_rule=rule
        )
        self.validation_results.append(result)
    
    def _check_completeness(self, data: Dict[str, Any]):
        """データ完全性チェック"""
        
        # 重要フィールドの存在確認
        critical_fields = ['app_id', 'name', 'type']
        for field in critical_fields:
            if field not in data or data[field] is None:
                self._add_result(
                    field, ValidationSeverity.CRITICAL,
                    f"必須フィールド '{field}' が欠落しています",
                    rule="completeness_check"
                )
        
        # 推奨フィールドの存在確認
        recommended_fields = ['developers', 'publishers', 'genres', 'release_date']
        missing_recommended = []
        
        for field in recommended_fields:
            if field not in data or data[field] is None or data[field] == []:
                missing_recommended.append(field)
        
        if missing_recommended:
            self._add_result(
                "metadata", ValidationSeverity.WARNING,
                f"推奨フィールドが不足: {', '.join(missing_recommended)}",
                rule="completeness_check"
            )
        
        # 説明文の品質チェック
        descriptions = ['detailed_description', 'short_description']
        for desc_field in descriptions:
            if desc_field in data and data[desc_field]:
                desc_text = data[desc_field]
                if len(desc_text) < 10:
                    self._add_result(
                        desc_field, ValidationSeverity.WARNING,
                        f"説明文が短すぎます ({len(desc_text)}文字)",
                        original_value=len(desc_text),
                        rule="completeness_check"
                    )
    
    def _check_consistency(self, data: Dict[str, Any]):
        """データ整合性チェック"""
        
        # 価格と無料フラグの整合性
        if data.get('is_free') and data.get('price_overview'):
            price_info = data['price_overview']
            if price_info.get('final', 0) > 0:
                self._add_result(
                    "pricing", ValidationSeverity.ERROR,
                    "無料ゲームなのに価格が設定されています",
                    original_value=price_info.get('final'),
                    rule="consistency_check"
                )
        
        # レビュー数の整合性（詳細版）
        positive = data.get('positive_reviews', 0) or 0
        negative = data.get('negative_reviews', 0) or 0
        total = data.get('total_reviews', 0) or 0
        
        if positive > 0 or negative > 0:
            calculated_total = positive + negative
            if total != calculated_total:
                difference = abs(total - calculated_total)
                self._add_result(
                    "reviews", ValidationSeverity.WARNING,
                    f"レビュー数の不整合: 宣言={total}, 計算={calculated_total}, 差={difference}",
                    original_value=total,
                    suggested_value=calculated_total,
                    rule="consistency_check"
                )
        
        # ジャンルとカテゴリの重複チェック
        genres = data.get('genres', []) or []
        categories = data.get('categories', []) or []
        
        if genres and categories:
            genre_names = {g.get('description', '').lower() for g in genres}
            category_names = {c.get('description', '').lower() for c in categories}
            overlap = genre_names & category_names
            
            if overlap:
                self._add_result(
                    "classification", ValidationSeverity.INFO,
                    f"ジャンルとカテゴリに重複があります: {list(overlap)}",
                    rule="consistency_check"
                )
    
    def _check_business_rules(self, data: Dict[str, Any]):
        """ビジネスルールチェック"""
        
        # インディーゲームの特徴チェック
        name = data.get('name', '').lower()
        developers = data.get('developers', []) or []
        publishers = data.get('publishers', []) or []
        
        # 大手パブリッシャーの検出
        major_publishers = [
            'valve', 'electronic arts', 'activision', 'ubisoft', 'bethesda',
            'square enix', 'capcom', 'bandai namco', 'sega', 'take-two'
        ]
        
        is_major_publisher = any(
            any(major in pub.lower() for major in major_publishers)
            for pub in publishers
        )
        
        if is_major_publisher:
            self._add_result(
                "classification", ValidationSeverity.INFO,
                f"大手パブリッシャーが関与: {publishers}",
                rule="business_rules"
            )
        
        # 価格帯の妥当性チェック
        if data.get('price_overview'):
            final_price = data['price_overview'].get('final', 0)
            if final_price > 0:
                price_in_dollars = final_price / 100  # セント表記の場合
                
                if price_in_dollars > 200:  # $200超
                    self._add_result(
                        "pricing", ValidationSeverity.WARNING,
                        f"異常に高い価格: ${price_in_dollars:.2f}",
                        original_value=price_in_dollars,
                        rule="business_rules"
                    )
                elif price_in_dollars < 0.5:  # $0.50未満
                    self._add_result(
                        "pricing", ValidationSeverity.INFO,
                        f"非常に安い価格: ${price_in_dollars:.2f}",
                        original_value=price_in_dollars,
                        rule="business_rules"
                    )
        
        # リリース日の妥当性
        if data.get('release_date') and data['release_date'].get('date'):
            try:
                # 簡単な日付解析（完全ではないが基本的なチェック）
                date_str = data['release_date']['date']
                current_year = datetime.now().year
                
                # 年の抽出（正規表現）
                year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
                if year_match:
                    year = int(year_match.group())
                    if year > current_year + 2:
                        self._add_result(
                            "release_date", ValidationSeverity.WARNING,
                            f"未来すぎるリリース日: {date_str}",
                            original_value=year,
                            rule="business_rules"
                        )
                    elif year < 1990:
                        self._add_result(
                            "release_date", ValidationSeverity.WARNING,
                            f"古すぎるリリース日: {date_str}",
                            original_value=year,
                            rule="business_rules"
                        )
            except Exception:
                pass  # 日付解析エラーは別途処理済み
    
    def _check_data_anomalies(self, data: Dict[str, Any]):
        """データ異常値検出"""
        
        # レビュー数の異常値検出
        total_reviews = data.get('total_reviews', 0) or 0
        if total_reviews > 1000000:  # 100万レビュー超
            self._add_result(
                "reviews", ValidationSeverity.INFO,
                f"非常に多くのレビュー数: {total_reviews:,}",
                original_value=total_reviews,
                rule="anomaly_detection"
            )
        
        # 推奨スコアの異常値
        rec_score = data.get('recommendation_score')
        if rec_score is not None:
            if rec_score > 100 or rec_score < 0:
                self._add_result(
                    "recommendation_score", ValidationSeverity.ERROR,
                    f"推奨スコアが範囲外: {rec_score}",
                    original_value=rec_score,
                    suggested_value=max(0, min(100, rec_score)),
                    rule="anomaly_detection"
                )
        
        # テキストフィールドの異常な長さ
        text_fields = {
            'name': 500,
            'short_description': 1000,
            'detailed_description': 50000
        }
        
        for field, max_length in text_fields.items():
            if data.get(field) and len(data[field]) > max_length:
                self._add_result(
                    field, ValidationSeverity.WARNING,
                    f"テキストが長すぎます: {len(data[field])}文字 (上限: {max_length})",
                    original_value=len(data[field]),
                    rule="anomaly_detection"
                )
    
    def get_quality_score(self) -> float:
        """データ品質スコアを計算
        
        Returns:
            0.0-1.0 の品質スコア
        """
        if not self.validation_results:
            return 1.0
        
        # 重要度別の重み付け
        severity_weights = {
            ValidationSeverity.INFO: 0.0,
            ValidationSeverity.WARNING: 0.2,
            ValidationSeverity.ERROR: 0.6,
            ValidationSeverity.CRITICAL: 1.0,
        }
        
        total_penalty = sum(
            severity_weights[result.severity]
            for result in self.validation_results
        )
        
        # 最大ペナルティ（全て CRITICAL の場合）を基準にスコア計算
        max_possible_penalty = len(self.validation_results) * 1.0
        
        if max_possible_penalty == 0:
            return 1.0
        
        quality_score = max(0.0, 1.0 - (total_penalty / max_possible_penalty))
        return quality_score
    
    def get_summary_report(self) -> Dict[str, Any]:
        """品質分析の要約レポートを生成
        
        Returns:
            分析結果の要約
        """
        severity_counts = {severity: 0 for severity in ValidationSeverity}
        
        for result in self.validation_results:
            severity_counts[result.severity] += 1
        
        return {
            "quality_score": self.get_quality_score(),
            "total_issues": len(self.validation_results),
            "severity_breakdown": {
                severity.value: count
                for severity, count in severity_counts.items()
            },
            "critical_issues": [
                result.message for result in self.validation_results
                if result.severity == ValidationSeverity.CRITICAL
            ],
            "recommendations": self._generate_recommendations(),
        }
    
    def _generate_recommendations(self) -> List[str]:
        """改善提案を生成"""
        recommendations = []
        
        # 重要度の高い問題に対する提案
        critical_issues = [
            result for result in self.validation_results
            if result.severity == ValidationSeverity.CRITICAL
        ]
        
        if critical_issues:
            recommendations.append("必須フィールドの欠落を修正してください")
        
        error_issues = [
            result for result in self.validation_results
            if result.severity == ValidationSeverity.ERROR
        ]
        
        if error_issues:
            recommendations.append("データ整合性エラーを修正してください")
        
        # フィールド別の提案
        field_issues = {}
        for result in self.validation_results:
            field = result.field_name
            if field not in field_issues:
                field_issues[field] = []
            field_issues[field].append(result)
        
        for field, issues in field_issues.items():
            if len(issues) >= 3:  # 同一フィールドに3つ以上の問題
                recommendations.append(f"フィールド '{field}' の品質改善が必要です")
        
        return recommendations


# 使用例とテスト
def test_data_validation():
    """データ検証のテスト"""
    
    print("🔍 データ検証テスト開始...")
    
    # テスト用ゲームデータ（問題のあるデータ）
    problematic_game_data = {
        "app_id": 12345,
        "name": "   Test Game   ",  # 前後に空白
        "type": "GAME",  # 大文字
        "is_free": True,
        "price_overview": {  # 無料なのに価格あり（矛盾）
            "currency": "USD",
            "initial": 1999,
            "final": 999
        },
        "developers": ["", "Valid Developer", "  "],  # 空の項目含む
        "positive_reviews": 100,
        "negative_reviews": 50,
        "total_reviews": 200,  # 矛盾した合計値
    }
    
    # 品質分析
    analyzer = DataQualityAnalyzer()
    results = analyzer.analyze_game_data(problematic_game_data)
    
    print(f"\n検証結果: {len(results)}件の問題を検出")
    
    for result in results:
        print(f"  [{result.severity.value.upper()}] {result.field_name}: {result.message}")
        if result.suggested_value is not None:
            print(f"    提案値: {result.suggested_value}")
    
    # 品質スコア
    quality_score = analyzer.get_quality_score()
    print(f"\n品質スコア: {quality_score:.2f}")
    
    # 要約レポート
    summary = analyzer.get_summary_report()
    print(f"\n要約:")
    print(f"  総問題数: {summary['total_issues']}")
    print(f"  重要度別: {summary['severity_breakdown']}")
    print(f"  改善提案:")
    for rec in summary['recommendations']:
        print(f"    - {rec}")
    
    print("\n✅ データ検証テスト完了!")


if __name__ == "__main__":
    test_data_validation()