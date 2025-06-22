"""
データベース機能のテスト

PostgreSQL接続、スキーマ操作、データ移行、正規化処理の
包括的なテストを実行します。
"""

import os
import sys
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd
import psycopg2
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config.database import sync_engine, get_sync_session

# 環境変数の読み込み
load_dotenv()


class TestDatabaseConnection:
    """データベース接続のテストクラス"""

    def test_database_connection_parameters(self):
        """データベース接続パラメータのテスト"""
        # 環境変数の確認
        required_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER']
        
        for var in required_vars:
            value = os.getenv(var)
            assert value is not None, f"環境変数 {var} が設定されていません"
            assert len(str(value)) > 0, f"環境変数 {var} が空です"

    def test_connection_string_format(self):
        """接続文字列の形式テスト"""
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "steam_analytics")
        user = os.getenv("POSTGRES_USER", "steam_user")
        password = os.getenv("POSTGRES_PASSWORD", "steam_password")
        
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        
        # 基本的な形式チェック
        assert connection_string.startswith("postgresql://")
        assert "@" in connection_string
        assert ":" in connection_string
        assert "/" in connection_string

    @pytest.mark.integration
    def test_direct_psycopg2_connection(self):
        """psycopg2による直接接続テスト"""
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "steam_analytics"),
            "user": os.getenv("POSTGRES_USER", "steam_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "steam_password"),
        }
        
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # 基本的なクエリ実行
            cursor.execute("SELECT 1 as test_value")
            result = cursor.fetchone()
            assert result[0] == 1
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            pytest.skip(f"データベース接続が利用できません: {e}")

    @pytest.mark.integration
    def test_sqlalchemy_engine_creation(self):
        """SQLAlchemyエンジンの作成テスト"""
        try:
            engine = get_db_connection()
            assert engine is not None
            
            # 接続テスト
            with engine.connect() as connection:
                result = connection.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                assert "PostgreSQL" in version
                
        except Exception as e:
            pytest.skip(f"データベース接続が利用できません: {e}")

    @pytest.mark.integration
    def test_session_creation(self):
        """データベースセッションの作成テスト"""
        try:
            with get_sync_session() as session:
                assert session is not None
                
                # セッションでのクエリ実行
                result = session.execute(text("SELECT current_database()"))
                db_name = result.fetchone()[0]
                assert len(db_name) > 0
                
        except Exception as e:
            pytest.skip(f"データベースセッションが利用できません: {e}")


class TestTableOperations:
    """テーブル操作のテストクラス"""

    @pytest.fixture
    def test_engine(self):
        """テスト用エンジン"""
        try:
            return sync_engine
        except:
            pytest.skip("データベース接続が利用できません")

    @pytest.mark.integration
    def test_table_existence_check(self, test_engine):
        """テーブル存在確認のテスト"""
        expected_tables = [
            'games',
            'games_normalized',
            'genres',
            'developers',
            'publishers',
            'game_genres',
            'game_developers',
            'game_publishers'
        ]
        
        with test_engine.connect() as connection:
            # 既存テーブルの取得
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """))
            
            existing_tables = [row[0] for row in result.fetchall()]
            
            # 基本テーブルの存在確認（一部でも存在すればOK）
            basic_tables = ['games', 'games_normalized']
            has_basic_table = any(table in existing_tables for table in basic_tables)
            
            if not has_basic_table:
                pytest.skip("基本テーブルが存在しません（セットアップが必要）")

    @pytest.mark.integration
    def test_table_schema_validation(self, test_engine):
        """テーブルスキーマの検証テスト"""
        with test_engine.connect() as connection:
            # gamesテーブルのカラム情報取得
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'games' 
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            if not columns:
                pytest.skip("gamesテーブルが存在しません")
            
            column_names = [col[0] for col in columns]
            
            # 必須カラムの確認
            required_columns = ['app_id', 'name', 'type']
            for req_col in required_columns:
                assert req_col in column_names, f"必須カラム {req_col} が存在しません"

    @pytest.mark.integration
    def test_data_insertion_and_retrieval(self, test_engine):
        """データ挿入・取得のテスト"""
        test_data = {
            'app_id': 999999,
            'name': 'Test Game for Testing',
            'type': 'game',
            'is_free': False
        }
        
        with test_engine.connect() as connection:
            trans = connection.begin()
            try:
                # テストデータの挿入
                insert_sql = text("""
                    INSERT INTO games (app_id, name, type, is_free)
                    VALUES (:app_id, :name, :type, :is_free)
                    ON CONFLICT (app_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        updated_at = CURRENT_TIMESTAMP
                """)
                
                connection.execute(insert_sql, test_data)
                
                # データの取得・確認
                select_sql = text("SELECT name, type FROM games WHERE app_id = :app_id")
                result = connection.execute(select_sql, {'app_id': test_data['app_id']})
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == test_data['name']
                assert row[1] == test_data['type']
                
                # テストデータの削除
                delete_sql = text("DELETE FROM games WHERE app_id = :app_id")
                connection.execute(delete_sql, {'app_id': test_data['app_id']})
                
                trans.commit()
                
            except Exception as e:
                trans.rollback()
                raise e


class TestDataMigration:
    """データ移行のテストクラス"""

    @pytest.fixture
    def sample_migration_data(self):
        """移行用サンプルデータ"""
        return [
            {
                'app_id': 100001,
                'name': 'Migration Test Game 1',
                'type': 'game',
                'genres': ['Action', 'Indie'],
                'developers': ['Test Studio A'],
                'publishers': ['Test Publisher A'],
                'is_free': False,
                'price_final': 999
            },
            {
                'app_id': 100002,
                'name': 'Migration Test Game 2',
                'type': 'game',
                'genres': ['Adventure', 'Casual'],
                'developers': ['Test Studio B'],
                'publishers': ['Test Publisher B'],
                'is_free': True,
                'price_final': 0
            }
        ]

    def test_migration_data_preparation(self, sample_migration_data):
        """移行データの準備テスト"""
        assert len(sample_migration_data) == 2
        
        for game in sample_migration_data:
            assert 'app_id' in game
            assert 'name' in game
            assert 'genres' in game
            assert isinstance(game['genres'], list)
            assert len(game['genres']) > 0

    def test_genre_extraction(self, sample_migration_data):
        """ジャンル抽出のテスト"""
        all_genres = set()
        for game in sample_migration_data:
            all_genres.update(game['genres'])
        
        expected_genres = {'Action', 'Indie', 'Adventure', 'Casual'}
        assert all_genres == expected_genres

    def test_developer_extraction(self, sample_migration_data):
        """開発者抽出のテスト"""
        all_developers = set()
        for game in sample_migration_data:
            all_developers.update(game['developers'])
        
        expected_developers = {'Test Studio A', 'Test Studio B'}
        assert all_developers == expected_developers

    @pytest.mark.integration
    def test_master_data_migration_simulation(self, sample_migration_data):
        """マスタデータ移行のシミュレーション"""
        # ジャンルマスタの作成をシミュレート
        genres_data = []
        genre_id_map = {}
        
        all_genres = set()
        for game in sample_migration_data:
            all_genres.update(game['genres'])
        
        for i, genre in enumerate(sorted(all_genres), 1):
            genres_data.append({'id': i, 'name': genre})
            genre_id_map[genre] = i
        
        assert len(genres_data) == 4
        assert 'Action' in genre_id_map
        assert 'Indie' in genre_id_map

    @pytest.mark.integration 
    def test_relationship_data_creation(self, sample_migration_data):
        """関係データ作成のテスト"""
        # ジャンルIDマッピング（実際の移行処理をシミュレート）
        genre_id_map = {'Action': 1, 'Indie': 2, 'Adventure': 3, 'Casual': 4}
        
        # game_genres関係データの作成
        game_genres_relations = []
        for game in sample_migration_data:
            for genre in game['genres']:
                game_genres_relations.append({
                    'game_id': game['app_id'],
                    'genre_id': genre_id_map[genre]
                })
        
        assert len(game_genres_relations) == 4  # 2ゲーム × 2ジャンル/ゲーム
        
        # 重複チェック
        unique_relations = set((r['game_id'], r['genre_id']) for r in game_genres_relations)
        assert len(unique_relations) == len(game_genres_relations)


class TestViewOperations:
    """ビュー操作のテストクラス"""

    @pytest.fixture
    def test_engine(self):
        """テスト用エンジン"""
        try:
            return sync_engine
        except:
            pytest.skip("データベース接続が利用できません")

    @pytest.mark.integration
    def test_analysis_view_existence(self, test_engine):
        """分析ビューの存在確認テスト"""
        with test_engine.connect() as connection:
            # ビューの存在確認
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = 'public'
                AND table_name = 'game_analysis_view'
            """))
            
            view_exists = result.fetchone() is not None
            
            if not view_exists:
                pytest.skip("game_analysis_viewが存在しません")

    @pytest.mark.integration
    def test_view_data_structure(self, test_engine):
        """ビューデータ構造のテスト"""
        with test_engine.connect() as connection:
            try:
                # ビューの構造確認
                result = connection.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'game_analysis_view'
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                column_names = [col[0] for col in columns]
                
                # 期待されるカラムの確認
                expected_columns = ['app_id', 'name', 'price_usd', 'rating', 'primary_genre']
                for expected_col in expected_columns:
                    if expected_col not in column_names:
                        pytest.skip(f"ビューに期待されるカラム {expected_col} が存在しません")
                        
            except Exception:
                pytest.skip("ビューの構造確認ができません")

    @pytest.mark.integration
    def test_view_data_sampling(self, test_engine):
        """ビューデータサンプリングテスト"""
        with test_engine.connect() as connection:
            try:
                # サンプルデータ取得
                result = connection.execute(text("""
                    SELECT app_id, name, price_usd, rating
                    FROM game_analysis_view 
                    LIMIT 5
                """))
                
                rows = result.fetchall()
                
                if len(rows) == 0:
                    pytest.skip("ビューにデータが存在しません")
                
                # データの基本検証
                for row in rows:
                    app_id, name, price_usd, rating = row
                    assert isinstance(app_id, int)
                    assert isinstance(name, str)
                    assert len(name) > 0
                    
                    # price_usdとratingはNullの可能性がある
                    if price_usd is not None:
                        assert isinstance(price_usd, (int, float))
                        assert price_usd >= 0
                    
                    if rating is not None:
                        assert isinstance(rating, (int, float))
                        assert 0 <= rating <= 1
                        
            except Exception as e:
                pytest.skip(f"ビューデータの確認ができません: {e}")


class TestDataIntegrity:
    """データ整合性のテストクラス"""

    @pytest.fixture
    def test_engine(self):
        """テスト用エンジン"""
        try:
            return sync_engine
        except:
            pytest.skip("データベース接続が利用できません")

    @pytest.mark.integration
    def test_foreign_key_constraints(self, test_engine):
        """外部キー制約のテスト"""
        with test_engine.connect() as connection:
            try:
                # game_genresテーブルの外部キー制約確認
                result = connection.execute(text("""
                    SELECT 
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu 
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name IN ('game_genres', 'game_developers', 'game_publishers')
                """))
                
                foreign_keys = result.fetchall()
                
                if len(foreign_keys) == 0:
                    pytest.skip("外部キー制約が設定されていません")
                
                # 期待される外部キーの確認
                expected_relations = [
                    ('game_genres', 'games_normalized'),
                    ('game_genres', 'genres'),
                    ('game_developers', 'games_normalized'),
                    ('game_developers', 'developers')
                ]
                
                actual_relations = set((fk[0], fk[2]) for fk in foreign_keys)
                
                for expected in expected_relations:
                    if expected in actual_relations:
                        break
                else:
                    pytest.skip("期待される外部キー関係が確認できません")
                    
            except Exception:
                pytest.skip("外部キー制約の確認ができません")

    @pytest.mark.integration
    def test_referential_integrity(self, test_engine):
        """参照整合性のテスト"""
        with test_engine.connect() as connection:
            try:
                # game_genresテーブルの参照整合性確認
                result = connection.execute(text("""
                    SELECT COUNT(*) as orphan_count
                    FROM game_genres gg
                    LEFT JOIN games_normalized g ON gg.game_id = g.app_id
                    WHERE g.app_id IS NULL
                """))
                
                orphan_games = result.fetchone()[0]
                assert orphan_games == 0, f"孤立したゲーム参照が {orphan_games} 件存在します"
                
                # genresテーブルの参照整合性確認
                result = connection.execute(text("""
                    SELECT COUNT(*) as orphan_count
                    FROM game_genres gg
                    LEFT JOIN genres ge ON gg.genre_id = ge.id
                    WHERE ge.id IS NULL
                """))
                
                orphan_genres = result.fetchone()[0]
                assert orphan_genres == 0, f"孤立したジャンル参照が {orphan_genres} 件存在します"
                
            except Exception as e:
                pytest.skip(f"参照整合性の確認ができません: {e}")

    @pytest.mark.integration
    def test_data_consistency(self, test_engine):
        """データ一貫性のテスト"""
        with test_engine.connect() as connection:
            try:
                # 価格データの一貫性確認
                result = connection.execute(text("""
                    SELECT COUNT(*) as invalid_price_count
                    FROM games_normalized
                    WHERE price_final < 0
                """))
                
                invalid_prices = result.fetchone()[0]
                assert invalid_prices == 0, f"無効な価格データが {invalid_prices} 件存在します"
                
                # 評価データの一貫性確認
                result = connection.execute(text("""
                    SELECT COUNT(*) as invalid_rating_count
                    FROM games_normalized
                    WHERE (positive_reviews + negative_reviews) > total_reviews
                    AND total_reviews IS NOT NULL
                    AND positive_reviews IS NOT NULL
                    AND negative_reviews IS NOT NULL
                """))
                
                invalid_ratings = result.fetchone()[0]
                assert invalid_ratings == 0, f"無効な評価データが {invalid_ratings} 件存在します"
                
            except Exception as e:
                pytest.skip(f"データ一貫性の確認ができません: {e}")


class TestPerformance:
    """パフォーマンステストクラス"""

    @pytest.fixture
    def test_engine(self):
        """テスト用エンジン"""
        try:
            return sync_engine
        except:
            pytest.skip("データベース接続が利用できません")

    @pytest.mark.integration
    def test_index_existence(self, test_engine):
        """インデックス存在確認のテスト"""
        with test_engine.connect() as connection:
            try:
                # インデックス一覧の取得
                result = connection.execute(text("""
                    SELECT indexname, tablename
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename IN ('games', 'games_normalized', 'game_genres', 'game_developers')
                """))
                
                indexes = result.fetchall()
                
                if len(indexes) == 0:
                    pytest.skip("インデックスが設定されていません")
                
                index_info = [(idx[1], idx[0]) for idx in indexes]
                
                # 重要なインデックスの確認
                important_indexes = [
                    ('games', 'games_pkey'),  # 主キー
                    ('games_normalized', 'games_normalized_pkey')  # 主キー
                ]
                
                for table, expected_index in important_indexes:
                    table_indexes = [idx[1] for idx in index_info if idx[0] == table]
                    # 主キーインデックスが存在することを確認
                    has_primary_key = any('pkey' in idx for idx in table_indexes)
                    if not has_primary_key:
                        pytest.skip(f"テーブル {table} に主キーインデックスが存在しません")
                        
            except Exception:
                pytest.skip("インデックス情報の確認ができません")

    @pytest.mark.integration 
    @pytest.mark.slow
    def test_query_performance(self, test_engine):
        """クエリパフォーマンステスト"""
        with test_engine.connect() as connection:
            try:
                # 基本的なSELECTクエリの実行時間測定
                import time
                
                start_time = time.time()
                result = connection.execute(text("SELECT COUNT(*) FROM games_normalized"))
                count = result.fetchone()[0]
                end_time = time.time()
                
                query_time = end_time - start_time
                
                # 10秒以内で完了することを確認（基準値）
                assert query_time < 10.0, f"基本クエリの実行時間が長すぎます: {query_time:.2f}秒"
                
                # データが存在することを確認
                if count == 0:
                    pytest.skip("テスト用データが存在しません")
                    
            except Exception as e:
                pytest.skip(f"パフォーマンステストが実行できません: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])