import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any, Set

# 定数定義
DATA_FILE_PATH = 'votes.json'
DATE_FORMAT = "%Y/%m/%d %H:%M"
DISPLAY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class VoteDataProcessor:
    """投票データの処理を行うクラス"""
    
    @staticmethod
    def load_vote_data(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
        """JSONファイルから投票データを読み込み、投票項目も抽出する"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # データが空の場合の処理
        if not data:
            return pd.DataFrame(), []
        
        df = pd.DataFrame(data)
        
        # データフレームが空の場合の処理
        if df.empty:
            return df, []
        
        df['vote_datetime'] = pd.to_datetime(df['vote_datetime'])
        
        # 全ての投票項目を抽出
        vote_columns = VoteDataProcessor._extract_vote_columns(df)
        
        return df, vote_columns
    
    @staticmethod
    def _extract_vote_columns(df: pd.DataFrame) -> List[str]:
        """データフレームから投票項目（カラム）を抽出する"""
        if df.empty:
            return []
        
        all_columns: Set[str] = set()
        
        for _, row in df.iterrows():
            if 'votes' in row and isinstance(row['votes'], dict):
                all_columns.update(row['votes'].keys())
        
        # ソートして一貫性を保つ
        return sorted(list(all_columns))
    
    @staticmethod
    def remove_duplicate_users(df: pd.DataFrame) -> pd.DataFrame:
        """同一ユーザーの重複投票を除去し、最新のデータのみを残す"""
        if df.empty:
            return df
        return df.sort_values('vote_datetime').groupby('username').tail(1).reset_index(drop=True)
    
    @staticmethod
    def calculate_vote_summary(df: pd.DataFrame, vote_columns: List[str]) -> Dict[str, int]:
        """各項目の総得票数を計算"""
        if df.empty or not vote_columns:
            return {}
        
        vote_summary = {}
        for column in vote_columns:
            votes = []
            for user_votes in df['votes']:
                # 項目が存在しない場合は0として扱う
                vote_value = user_votes.get(column, 0)
                # 数値でない場合は0として扱う
                try:
                    votes.append(int(vote_value))
                except (ValueError, TypeError):
                    votes.append(0)
            vote_summary[column] = sum(votes)
        return vote_summary
    
    @staticmethod
    def prepare_display_data(df: pd.DataFrame, vote_columns: List[str]) -> pd.DataFrame:
        """表示用のデータフレームを準備"""
        if df.empty:
            return pd.DataFrame()
        
        display_data = []
        for _, row in df.iterrows():
            vote_data = {
                'ユーザー名': row['username'],
                '投票日時': row['vote_datetime'].strftime(DISPLAY_DATE_FORMAT)
            }
            # 動的に投票項目を追加
            for column in vote_columns:
                vote_value = row['votes'].get(column, 0)
                try:
                    vote_data[column] = int(vote_value)
                except (ValueError, TypeError):
                    vote_data[column] = 0
            
            display_data.append(vote_data)
        
        return pd.DataFrame(display_data)

class VoteVisualizer:
    """投票データの可視化を行うクラス"""
    
    @staticmethod
    def create_stacked_bar_chart(df: pd.DataFrame, vote_columns: List[str]) -> go.Figure:
        """ユーザー別投票の積み上げ横棒グラフを作成（インタラクティブ）"""
        # データが空の場合は空のグラフを返す
        if df.empty or not vote_columns:
            fig = go.Figure()
            fig.update_layout(
                title=dict(
                    text='データがありません',
                    font=dict(size=16),
                    x=0.5
                ),
                xaxis=dict(title='総得票数'),
                yaxis=dict(title=''),
                height=400,
                annotations=[
                    dict(
                        text="投票データがありません",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        xanchor='center', yanchor='middle',
                        font=dict(size=20, color='gray'),
                        showarrow=False
                    )
                ]
            )
            return fig
        
        # 総得票数を計算して降順でソート
        vote_summary = VoteDataProcessor.calculate_vote_summary(df, vote_columns)
        sorted_items = sorted(vote_summary.items(), key=lambda x: x[1], reverse=True)
        sorted_activities = [item[0] for item in sorted_items]
        
        # ユーザー別の投票データを準備
        user_votes_data = VoteVisualizer._prepare_user_votes_data(df, sorted_activities)
        
        # Plotlyでインタラクティブグラフを作成
        fig = go.Figure()
        
        # カラーパレットを設定
        colors = px.colors.qualitative.Set3
        
        # 各ユーザーの投票データを積み上げ横棒グラフに追加
        for i, (username, votes) in enumerate(user_votes_data.items()):
            # ホバーテキストを準備
            hover_texts = []
            for j, (activity, vote_count) in enumerate(zip(sorted_activities, votes)):
                if vote_count > 0:
                    hover_texts.append(f"{username}: {vote_count}票<br>項目: {activity}")
                else:
                    hover_texts.append(f"{username}: 0票<br>項目: {activity}")
            
            fig.add_trace(go.Bar(
                name=username,
                y=sorted_activities,
                x=votes,
                orientation='h',
                marker=dict(
                    color=colors[i % len(colors)],
                    opacity=0.8
                ),
                hovertemplate='<b>%{hovertext}</b><extra></extra>',
                hovertext=hover_texts,
                showlegend=True
            ))
        
        # グラフのスタイリング
        VoteVisualizer._style_plotly_chart(fig, sorted_activities, vote_summary)
        
        return fig
    
    @staticmethod
    def _prepare_user_votes_data(df: pd.DataFrame, sorted_activities: List[str]) -> Dict[str, List[int]]:
        """ユーザー別の投票データを準備"""
        user_votes_data = {}
        for _, row in df.iterrows():
            username = row['username']
            user_votes = []
            for activity in sorted_activities:
                vote_value = row['votes'].get(activity, 0)
                try:
                    user_votes.append(int(vote_value))
                except (ValueError, TypeError):
                    user_votes.append(0)
            user_votes_data[username] = user_votes
        return user_votes_data
    
    @staticmethod
    def _style_plotly_chart(fig: go.Figure, sorted_activities: List[str], vote_summary: Dict[str, int]) -> None:
        """Plotlyグラフのスタイリングを適用"""
        # 総得票数を計算
        total_votes = [vote_summary[activity] for activity in sorted_activities]
        
        # レイアウトを設定
        fig.update_layout(
            title=dict(
                text='総得票数（ユーザー別積み上げ）',
                font=dict(size=16),
                x=0.5
            ),
            xaxis=dict(
                title='総得票数',
                titlefont=dict(size=14),
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            yaxis=dict(
                title='',
                categoryorder='array',
                categoryarray=sorted_activities,
                autorange='reversed'
            ),
            barmode='stack',
            height=600,
            margin=dict(l=150, r=100, t=60, b=60),
            legend=dict(
                orientation="v",
                x=1.02,
                y=1,
                xanchor="left",
                yanchor="top"
            ),
            font=dict(family="Arial, sans-serif"),
            hovermode='closest'
        )
        
        # 総得票数のアノテーションを追加
        for activity, total in zip(sorted_activities, total_votes):
            if total > 0:  # 0票の場合は表示しない
                fig.add_annotation(
                    x=total,
                    y=activity,
                    text=f'<b>{total}票</b>',
                    showarrow=False,
                    font=dict(size=12, color='black'),
                    xanchor='left',
                    yanchor='middle',
                    xshift=5  # 棒グラフから少し右にずらす
                )
        
        # X軸の範囲を調整（アノテーション用の余白を含む）
        max_votes = max(total_votes) if total_votes else 0
        fig.update_xaxes(range=[0, max_votes * 1.2])  # 20%の余白を確保

class VoteStatistics:
    """投票統計情報を計算するクラス"""
    
    @staticmethod
    def calculate_basic_stats(df_original: pd.DataFrame, df_processed: pd.DataFrame) -> Dict[str, Any]:
        """基本統計情報を計算"""
        if df_processed.empty:
            return {
                'total_votes': 0,
                'unique_voters': 0,
                'duplicate_voters': 0,
                'latest_vote_time': 'データなし'
            }
        
        latest_vote = df_processed['vote_datetime'].max()
        return {
            'total_votes': len(df_original),
            'unique_voters': len(df_processed),
            'duplicate_voters': len(df_original) - len(df_processed),
            'latest_vote_time': latest_vote.strftime(DATE_FORMAT)
        }

class StreamlitUI:
    """Streamlitユーザーインターフェースを管理するクラス"""
    
    @staticmethod
    def setup_page():
        """ページの基本設定"""
        st.set_page_config(
            page_title="投票データ可視化",
            page_icon="📊",
            layout="wide"
        )
        st.title("🗳️ 投票データ可視化")
        st.markdown("---")
    
    @staticmethod
    def display_metrics(stats: Dict[str, Any]) -> None:
        """メトリクス情報を表示"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総投票者数", stats['total_votes'])
        with col2:
            st.metric("ユニーク投票者数", stats['unique_voters'])
        with col3:
            st.metric("重複投票者数", stats['duplicate_voters'])
        with col4:
            st.metric("最新投票日時", stats['latest_vote_time'])
    
    @staticmethod
    def display_vote_summary(vote_summary: Dict[str, int]) -> None:
        """得票数詳細を表示"""
        st.subheader("📈 得票数詳細")
        if not vote_summary:
            st.info("投票データがありません")
            return
        
        for activity, score in sorted(vote_summary.items(), 
                                    key=lambda x: x[1], reverse=True):
            st.metric(activity, f"{score}票")
    
    @staticmethod
    def display_main_visualization(df: pd.DataFrame, vote_columns: List[str], vote_summary: Dict[str, int]) -> None:
        """メインの可視化を表示"""
        st.subheader("📊 総得票数")
        
        if df.empty:
            st.info("📝 投票データがありません。votes.jsonファイルにデータを追加してください。")
            return
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            fig = VoteVisualizer.create_stacked_bar_chart(df, vote_columns)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            StreamlitUI.display_vote_summary(vote_summary)
    
    @staticmethod
    def display_data_table(df: pd.DataFrame, vote_columns: List[str]) -> None:
        """データテーブルを表示"""
        st.subheader("📋 処理済み投票データ詳細")
        
        if df.empty:
            st.info("表示するデータがありません")
            return
        
        display_df = VoteDataProcessor.prepare_display_data(df, vote_columns)
        st.dataframe(display_df, use_container_width=True)
    
    @staticmethod
    def display_empty_data_message() -> None:
        """データが空の場合のメッセージを表示"""
        st.info("📄 votes.jsonファイルは存在しますが、データが空です。")
        st.markdown("### 💡 データを追加する方法")
        st.markdown("1. votes.jsonファイルに投票データを追加してください")
        st.markdown("2. ページを更新すると結果が表示されます")
        StreamlitUI.display_error_messages()
    
    @staticmethod
    def display_error_messages() -> None:
        """エラーメッセージとサンプルデータを表示"""
        sample_data = [
          {
            "username": "山田花子",
            "votes": {
              "温泉": 9,
              "BBQ": 4,
              "テーマパーク": 1,
              "ハイキング": 1
            },
            "vote_datetime": "2025-07-01 20:22:17"
          },
          {
            "username": "鈴木太郎",
            "votes": {
              "温泉": 5,
              "BBQ": 5,
              "テーマパーク": 5,
              "ハイキング": 5
            },
            "vote_datetime": "2025-07-01 20:22:44"
          },
          {
            "username": "田中桃子",
            "votes": {
              "温泉": 0,
              "BBQ": 0,
              "テーマパーク": 6,
              "ハイキング": 8
            },
            "vote_datetime": "2025-07-01 20:23:28"
          }
        ]
        
        st.subheader("📝 期待されるデータ形式")
        st.info("💡 投票項目は自動的に検出されます。異なるユーザーが異なる項目に投票しても対応可能です。")
        st.json(sample_data)

def main():
    """メイン処理"""
    StreamlitUI.setup_page()
    
    try:
        # データ読み込みと処理
        df_original, vote_columns = VoteDataProcessor.load_vote_data(DATA_FILE_PATH)
        df_processed = VoteDataProcessor.remove_duplicate_users(df_original)
        
        # データが空の場合の処理
        if df_processed.empty:
            # 統計情報計算（空データ用）
            stats = VoteStatistics.calculate_basic_stats(df_original, df_processed)
            vote_summary = {}
            
            # UI表示（空データ用）
            StreamlitUI.display_metrics(stats)
            st.markdown("---")
            
            StreamlitUI.display_empty_data_message()
            return
        
        # 統計情報計算
        stats = VoteStatistics.calculate_basic_stats(df_original, df_processed)
        vote_summary = VoteDataProcessor.calculate_vote_summary(df_processed, vote_columns)
        
        # UI表示
        StreamlitUI.display_metrics(stats)
        st.markdown("---")
        
        StreamlitUI.display_main_visualization(df_processed, vote_columns, vote_summary)
        st.markdown("---")
        
        StreamlitUI.display_data_table(df_processed, vote_columns)
        
    except FileNotFoundError:
        st.error("❌ 'votes.json' ファイルが見つかりません")
        st.info("📁 同一フォルダに 'votes.json' ファイルを配置してください")
        StreamlitUI.display_error_messages()
        
    except json.JSONDecodeError as e:
        st.error(f"❌ JSONファイルの形式が正しくありません: {str(e)}")
        st.info("📝 ファイルの内容を確認してください")
        
    except Exception as e:
        st.error(f"❌ データの読み込みエラー: {str(e)}")
        st.info("📞 管理者にお問い合わせください")

if __name__ == "__main__":
    main()