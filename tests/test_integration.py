"""
統合テスト

システム全体の統合機能を検証するテストスイートです。
実際のデータフローとエンドツーエンドの動作を確認します。
"""

import os
import sys
from typing import Any, Dict, List

import pytest

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestSystemIntegration:
    """システム統合テストクラス"""

    def test_project_structure(self):
        """プロジェクト構造の検証"""
        # 重要なディレクトリの存在確認
        important_dirs = [
            'src',
            'src/analyzers',
            'src/collectors', 
            'src/config',
            'src/dashboard',
            'tests',
            'docs'
        ]
        
        for dir_path in important_dirs:
            full_path = os.path.join('/workspace', dir_path)
            assert os.path.exists(full_path), f"ディレクトリ {dir_path} が存在しません"

    def test_required_files(self):
        """必須ファイルの存在確認"""
        required_files = [
            'README.md',
            'requirements.txt',
            'pytest.ini',
            '.env.example',
            'docker-compose.yml',
            'collect_indie_games.py'
        ]
        
        for file_path in required_files:
            full_path = os.path.join('/workspace', file_path)
            assert os.path.exists(full_path), f"必須ファイル {file_path} が存在しません"

    def test_python_imports(self):
        """主要Pythonモジュールのインポートテスト"""
        # データ収集モジュール
        try:
            from collect_indie_games import IndieGameCollector
            assert IndieGameCollector is not None
        except ImportError as e:
            pytest.fail(f"IndieGameCollectorのインポートに失敗: {e}")

        # 設定モジュール
        try:
            from src.config.database import sync_engine
            assert sync_engine is not None
        except ImportError as e:
            pytest.fail(f"データベース設定のインポートに失敗: {e}")

    def test_environment_setup(self):
        """環境設定の基本検証"""
        # 環境変数ファイルの確認
        env_example = '/workspace/.env.example'
        env_file = '/workspace/.env'
        
        assert os.path.exists(env_example), ".env.exampleが存在しません"
        
        if os.path.exists(env_file):
            # .envファイルが存在する場合の基本検証
            with open(env_file, 'r') as f:
                env_content = f.read()
                assert 'POSTGRES_HOST' in env_content
                assert 'POSTGRES_PORT' in env_content

    def test_database_schema_compatibility(self):
        """データベーススキーマの基本互換性確認"""
        try:
            from src.config.database import sync_engine
            from sqlalchemy import text
            
            with sync_engine.connect() as connection:
                # 基本的なテーブル存在確認
                result = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                
                tables = [row[0] for row in result.fetchall()]
                
                # 少なくとも1つのゲーム関連テーブルが存在することを確認
                game_tables = [t for t in tables if 'game' in t.lower()]
                assert len(game_tables) > 0, "ゲーム関連テーブルが見つかりません"
                
        except Exception as e:
            pytest.skip(f"データベース接続が利用できません: {e}")

    def test_configuration_consistency(self):
        """設定の一貫性確認"""
        # requirements.txtの基本検証
        with open('/workspace/requirements.txt', 'r') as f:
            requirements = f.read()
            
            # 重要な依存関係の確認
            essential_packages = [
                'pandas',
                'sqlalchemy',
                'streamlit',
                'plotly',
                'psycopg2-binary'
            ]
            
            for package in essential_packages:
                assert package in requirements.lower(), f"必須パッケージ {package} がrequirements.txtに含まれていません"

    def test_documentation_structure(self):
        """ドキュメント構造の確認"""
        docs_dir = '/workspace/docs'
        
        if os.path.exists(docs_dir):
            doc_files = os.listdir(docs_dir)
            
            # 重要なドキュメントファイルの確認
            important_docs = [
                'ARCHITECTURE.md',
                'API_REFERENCE.md',
                'DEPLOYMENT_GUIDE.md'
            ]
            
            for doc in important_docs:
                if doc in doc_files:
                    # ドキュメントファイルが空でないことを確認
                    doc_path = os.path.join(docs_dir, doc)
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        assert len(content) > 100, f"ドキュメント {doc} の内容が不十分です"

    def test_test_suite_structure(self):
        """テストスイート構造の確認"""
        tests_dir = '/workspace/tests'
        test_files = os.listdir(tests_dir)
        
        # 主要なテストファイルの存在確認
        expected_test_files = [
            'test_db_connection.py',
            'test_collectors.py',
            'test_analyzers.py',
            'test_database.py',
            'test_dashboard.py'
        ]
        
        for test_file in expected_test_files:
            assert test_file in test_files, f"テストファイル {test_file} が存在しません"

    def test_code_quality_tools(self):
        """コード品質ツールの設定確認"""
        # pytest.iniの確認
        pytest_ini = '/workspace/pytest.ini'
        assert os.path.exists(pytest_ini), "pytest.iniが存在しません"
        
        with open(pytest_ini, 'r') as f:
            pytest_content = f.read()
            assert 'testpaths' in pytest_content
            assert 'cov' in pytest_content  # カバレッジ設定の確認

    def test_container_configuration(self):
        """コンテナ設定の基本確認"""
        docker_compose = '/workspace/docker-compose.yml'
        assert os.path.exists(docker_compose), "docker-compose.ymlが存在しません"
        
        with open(docker_compose, 'r') as f:
            compose_content = f.read()
            
            # 重要なサービスの確認
            essential_services = ['postgres', 'redis']
            for service in essential_services:
                assert service in compose_content, f"サービス {service} がdocker-compose.ymlに含まれていません"


class TestDataFlow:
    """データフロー統合テストクラス"""

    def test_basic_data_collection_flow(self):
        """基本的なデータ収集フローの検証"""
        try:
            from collect_indie_games import IndieGameCollector
            
            # コレクターの初期化
            collector = IndieGameCollector()
            
            # 基本的な設定の確認
            assert hasattr(collector, 'indie_keywords')
            assert hasattr(collector, 'major_publishers')
            assert len(collector.indie_keywords) > 0
            assert len(collector.major_publishers) > 0
            
        except Exception as e:
            pytest.fail(f"基本データ収集フローの検証に失敗: {e}")

    def test_indie_game_classification_logic(self):
        """インディーゲーム分類ロジックの検証"""
        from collect_indie_games import IndieGameCollector
        
        collector = IndieGameCollector()
        
        # 典型的なインディーゲームケース
        indie_game = {
            "steam_appid": 12345,
            "name": "Test Indie Game",
            "type": "game",
            "developers": ["Small Studio"],
            "publishers": ["Small Studio"],
            "genres": [{"description": "Indie"}, {"description": "Action"}]
        }
        
        assert collector.is_indie_game(indie_game) is True
        
        # 大手パブリッシャーケース
        major_game = {
            "steam_appid": 67890,
            "name": "AAA Game",
            "type": "game",
            "developers": ["Big Studio"],
            "publishers": ["Electronic Arts"],
            "genres": [{"description": "Action"}]
        }
        
        assert collector.is_indie_game(major_game) is False

    def test_data_quality_validation(self):
        """データ品質バリデーションの検証"""
        from collect_indie_games import IndieGameCollector
        
        collector = IndieGameCollector()
        
        # 不完全なデータケース
        incomplete_data = {
            "steam_appid": 11111,
            # nameなし
            "type": "game"
        }
        
        assert collector.is_indie_game(incomplete_data) is False
        
        # DLCケース
        dlc_data = {
            "steam_appid": 22222,
            "name": "Game DLC Pack",
            "type": "game",
            "genres": [{"description": "Indie"}],
            "developers": ["Studio"]
        }
        
        assert collector.is_indie_game(dlc_data) is False


class TestSystemResilience:
    """システム耐障害性テストクラス"""

    def test_configuration_fallbacks(self):
        """設定フォールバックの検証"""
        from src.config.database import DatabaseConfig
        
        # 環境変数なしでもデフォルト値で動作することを確認
        import os
        original_host = os.environ.get('POSTGRES_HOST')
        
        try:
            # 環境変数を一時的に削除
            if 'POSTGRES_HOST' in os.environ:
                del os.environ['POSTGRES_HOST']
            
            config = DatabaseConfig()
            
            # デフォルト値が設定されることを確認
            assert config.host is not None
            assert len(config.host) > 0
            
        finally:
            # 環境変数を復元
            if original_host:
                os.environ['POSTGRES_HOST'] = original_host

    def test_error_handling_patterns(self):
        """エラーハンドリングパターンの検証"""
        from collect_indie_games import IndieGameCollector
        
        collector = IndieGameCollector()
        
        # Noneデータの処理
        result = collector.is_indie_game(None)
        assert result is False
        
        # 空辞書の処理
        result = collector.is_indie_game({})
        assert result is False
        
        # 不正な型の処理
        result = collector.is_indie_game("invalid_data")
        assert result is False

    def test_resource_management(self):
        """リソース管理の検証"""
        # フォールバックゲームリストのテスト
        from collect_indie_games import IndieGameCollector
        
        collector = IndieGameCollector()
        fallback_list = collector.get_fallback_game_list(10)
        
        assert isinstance(fallback_list, list)
        assert len(fallback_list) <= 10
        assert all(isinstance(app_id, int) for app_id in fallback_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])