import streamlit as st
import json
import os
import plotly.express as px
import pandas as pd
from datetime import datetime


class VotingApp:
    """Quadratic Voting アプリケーションのメインクラス"""
    
    def __init__(self):
        self.config = self.load_config()
        self.init_session_state()
    
    def load_config(self):
        """設定ファイルの読み込み"""
        script_dir = os.path.dirname(__file__)
        config_path = os.path.join(script_dir, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def init_session_state(self):
        """セッション状態の初期化"""
        if "user_votes" not in st.session_state:
            st.session_state.user_votes = {opt: 0 for opt in self.config["options"]}
        if "vote_completed" not in st.session_state:
            st.session_state.vote_completed = False
        if "show_confirm_dialog" not in st.session_state:
            st.session_state.show_confirm_dialog = False
        if "balloons_shown" not in st.session_state:
            st.session_state.balloons_shown = False
    
    def load_votes(self):
        """投票結果の読み込み"""
        if not os.path.exists("votes.json") or os.path.getsize("votes.json") == 0:
            return []
        with open("votes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save_votes(self, votes):
        """投票結果の保存"""
        with open("votes.json", "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)
    
    def calculate_max_votes_for_option(self, option):
        """指定した選択肢に対する最大投票数を計算"""
        other_options_cost = sum(
            v ** 2 for k, v in st.session_state.user_votes.items() if k != option
        )
        remaining_credits = max(0, self.config["credits"] - other_options_cost)
        theoretical_max = int(remaining_credits ** 0.5)
        
        # 複数選択肢がある場合は1つの項目に全クレジットを使うことを禁止
        if len(self.config["options"]) > 1:
            max_per_option = int((self.config["credits"] - 1) ** 0.5)
            return min(theoretical_max, max_per_option)
        return theoretical_max
    
    def can_vote_more(self):
        """追加投票が可能かどうかを判定"""
        remaining_credits = self.get_remaining_credits()
        
        for option in self.config["options"]:
            current_votes = st.session_state.user_votes[option]
            cost_for_next_vote = (current_votes + 1) ** 2 - current_votes ** 2
            
            # 単一項目全クレジット制限のチェック
            would_exceed_single_limit = (
                len(self.config["options"]) > 1 and 
                (current_votes + 1) ** 2 >= self.config["credits"]
            )
            
            if remaining_credits >= cost_for_next_vote and not would_exceed_single_limit:
                return True
        return False
    
    def get_total_cost(self):
        """総使用クレジットを計算"""
        return sum(v ** 2 for v in st.session_state.user_votes.values())
    
    def get_remaining_credits(self):
        """残りクレジットを計算"""
        return self.config["credits"] - self.get_total_cost()
    
    def render_credit_chart(self):
        """クレジット使用状況の円グラフを作成"""
        chart_data = []
        
        # 各選択肢の使用クレジット
        for option, votes in st.session_state.user_votes.items():
            if votes > 0:
                cost = votes ** 2
                chart_data.append({
                    "項目": f"{option} ({votes}票)",
                    "クレジット": cost,
                    "タイプ": "使用済み"
                })
        
        # 残りクレジット
        remaining_credits = self.get_remaining_credits()
        if remaining_credits > 0:
            chart_data.append({
                "項目": "未使用",
                "クレジット": remaining_credits,
                "タイプ": "未使用"
            })
        
        if not chart_data:
            return None
        
        df = pd.DataFrame(chart_data).sort_values("クレジット", ascending=False)
        
        # 色の設定
        color_map = {}
        base_colors = px.colors.qualitative.Set3
        color_index = 0
        
        for _, row in df.iterrows():
            if row["タイプ"] == "未使用":
                color_map[row["項目"]] = "#E8E8E8"
            else:
                color_map[row["項目"]] = base_colors[color_index % len(base_colors)]
                color_index += 1
        
        colors = [color_map[item] for item in df["項目"]]
        
        fig = px.pie(df, values="クレジット", names="項目", color_discrete_sequence=colors)
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>クレジット: %{value}<br>割合: %{percent}<br><extra></extra>',
            sort=False,
            direction="clockwise",
            rotation=0
        )
        fig.update_layout(
            showlegend=True,
            width=500,
            height=400,
            margin=dict(t=50, b=50, l=50, r=50),
            transition_duration=0
        )
        
        return fig
    
    def complete_vote(self, username):
        """投票完了処理"""
        vote_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        all_votes = self.load_votes()
        all_votes.append({
            "username": username,
            "votes": st.session_state.user_votes,
            "vote_datetime": vote_datetime
        })
        self.save_votes(all_votes)
        
        st.session_state.vote_completed = True
        st.session_state.vote_datetime = vote_datetime  # 投票確定日時を保存
        st.session_state.show_confirm_dialog = False  # 確認ダイアログを閉じる
    
    def update_vote(self, option):
        """投票数更新のコールバック関数"""
        new_value = st.session_state[f"vote_{option}"]
        st.session_state.user_votes[option] = new_value
    
    def render_voting_interface(self):
        """投票インターフェースの描画"""
        cols = st.columns(len(self.config["options"]))
        
        for i, option in enumerate(self.config["options"]):
            with cols[i]:
                max_votes = self.calculate_max_votes_for_option(option)
                current_votes = st.session_state.user_votes.get(option, 0)
                
                new_votes = st.number_input(
                    f"{option}への投票数",
                    min_value=0,
                    max_value=max_votes,
                    value=min(current_votes, max_votes),
                    step=1,
                    key=f"vote_{option}",
                    on_change=lambda opt=option: self.update_vote(opt)
                )
                
                st.write(f"消費クレジット: {new_votes ** 2}")
    
    def render_credit_status(self):
        """クレジット状況の表示"""
        st.markdown("---")
        
        total_cost = self.get_total_cost()
        remaining_credits = self.get_remaining_credits()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="総クレジット", value=self.config["credits"])
        with col2:
            st.metric(label="使用クレジット", value=total_cost)
        with col3:
            st.metric(label="残りクレジット", value=remaining_credits)
        
        # 円グラフの表示
        fig = self.render_credit_chart()
        if fig:
            chart_key = f"chart_{hash(str(sorted(st.session_state.user_votes.items())))}"
            st.plotly_chart(fig, use_container_width=True, key=chart_key)
        else:
            st.info("まだ投票が行われていません。")
    
    def validate_votes(self):
        """投票の妥当性を検証"""
        total_cost = self.get_total_cost()
        
        # クレジット超過チェック
        if total_cost > self.config["credits"]:
            st.error("クレジットの上限を超えています。投票数を見直してください。")
            return False
        
        # 単一項目全クレジット制限チェック
        if len(self.config["options"]) > 1:
            for vote_num in st.session_state.user_votes.values():
                if vote_num ** 2 >= self.config["credits"]:
                    st.error("1つの項目に全クレジットを投じることはできません。")
                    return False
        
        return True
    
    def render_voting_buttons(self, username):
        """投票ボタンの描画と処理"""
        if st.session_state.vote_completed:
            # バルーンは1回だけ表示する
            if not st.session_state.balloons_shown:
                st.balloons()
                st.session_state.balloons_shown = True
            
            st.success("投票が完了しました！")
            st.write("ご協力ありがとうございました！")
            if hasattr(st.session_state, 'vote_datetime'):
                st.write(f"投票確定日時: {st.session_state.vote_datetime}")
            st.info("このタブを閉じてアプリを終了してください。")
            return
        
        total_cost = self.get_total_cost()
        remaining_credits = self.get_remaining_credits()
        can_still_vote = self.can_vote_more()
        
        # 確認ダイアログの表示
        if st.session_state.show_confirm_dialog:
            st.warning("この内容で投票を確定しますか？")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("はい", key="confirm_yes"):
                    self.complete_vote(username)
                    st.rerun()
            with col2:
                if st.button("いいえ", key="confirm_no"):
                    st.session_state.show_confirm_dialog = False
                    st.rerun()
            return
        
        # 常にメッセージエリアを表示してレイアウト変化を防ぐ
        if remaining_credits > 0 and not can_still_vote:
            st.warning("この投票内容ではクレジットを使い切れませんが、このまま投票を確定しますか？")
            if st.button("はい、このまま投票します"):
                self.complete_vote(username)
                st.rerun()
            return  # ここでreturnして「投票を確定する」ボタンを表示しない
        elif remaining_credits > 0 and can_still_vote:
            st.info("クレジットは使い切ってください。")
        else:
            # クレジットを使い切った場合は成功メッセージを表示
            st.success("クレジットをすべて使い切りました。投票を確定できます。")
        
        # 投票確定ボタン（クレジットが残っているが追加投票できない場合は表示しない）
        disable_vote_button = (remaining_credits > 0 and can_still_vote)
        
        if st.button("投票を確定する", disabled=disable_vote_button):
            if remaining_credits == 0:
                # クレジットを使い切った場合は直接投票
                self.complete_vote(username)
                st.rerun()
            else:
                # クレジットが残っている場合は確認ダイアログを表示
                st.session_state.show_confirm_dialog = True
                st.rerun()
    
    def run(self):
        """アプリケーションのメイン実行"""
        st.set_page_config(page_title="Quadratic Voting", layout="centered")
        
        st.title(self.config["title"])
        
        # ユーザー名入力
        st.info("投票を開始するには、名前を入力してください。")
        username = st.text_input("あなたの名前を入力してください", key="username")
        
        if not username:
            st.stop()
        
        # ユーザー名が変更された場合の処理
        if "last_username" not in st.session_state or st.session_state.last_username != username:
            st.session_state.vote_completed = False
            st.session_state.show_confirm_dialog = False
            st.session_state.balloons_shown = False
            st.session_state.last_username = username
        
        st.header(f"ようこそ、{username}さん！")
        st.write(f"あなたには **{self.config['credits']}** の投票クレジットが与えられています。")
        st.markdown("---")
        
        # 投票インターフェース
        self.render_voting_interface()
        
        # 各投票数を現在の入力値で更新（互換性のため）
        for option in self.config["options"]:
            if f"vote_{option}" in st.session_state:
                st.session_state.user_votes[option] = st.session_state[f"vote_{option}"]
        
        # 投票ボタン
        self.render_voting_buttons(username)
        
        # クレジット状況表示
        self.render_credit_status()
        
        st.markdown("---")
        
        # 投票検証
        if not self.validate_votes():
            st.stop()

def main():
    """メイン関数"""
    try:
        app = VotingApp()
        app.run()
    except FileNotFoundError:
        st.error("設定ファイル `config.json` が見つかりません。")


if __name__ == "__main__":
    main()