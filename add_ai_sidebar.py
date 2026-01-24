import os

# AIサイドバーを追加するページ
pages = [
    'pages/02_情報入力.py',
    'pages/03_モデル設定.py',
    'pages/05_ページ詳細.py',
    'pages/06_出力.py',
]

import_line = "from modules.ai_sidebar import render_ai_sidebar\n"
call_line = "    render_ai_sidebar()\n"

for page in pages:
    if os.path.exists(page):
        with open(page, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 既に追加済みならスキップ
        if 'render_ai_sidebar' in content:
            print(f"⏭️ {page} - 既に追加済み")
            continue
        
        # import追加（require_product()の後に）
        if 'require_product()' in content:
            content = content.replace(
                'require_product()\n',
                'require_product()\n\n' + import_line
            )
        
        # 関数呼び出し追加（st.title の後を探す）
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if "st.title(" in line and "render_ai_sidebar()" not in content:
                new_lines.append("    ")
                new_lines.append("    # AIサイドバー表示")
                new_lines.append("    render_ai_sidebar()")
        
        content = '\n'.join(new_lines)
        
        with open(page, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {page} - 追加完了")

print("\n全ページ更新完了！")
