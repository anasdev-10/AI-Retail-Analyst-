import sys

content = open('app.py', 'r', encoding='utf-8').read()

lines = content.split('\n')
out_lines = []

in_ui_section = False
for i, line in enumerate(lines):
    if line.startswith('# ── 5. SIDEBAR ─────────────────────────────────────────────────────────────────'):
        out_lines.append(line)
        out_lines.append('def main_ui():')
        in_ui_section = True
        continue
        
    if in_ui_section:
        if line == '':
            out_lines.append('')
        else:
            out_lines.append('    ' + line)
    else:
        out_lines.append(line)

if in_ui_section:
    out_lines.append('')
    out_lines.append('if __name__ == \'__main__\':')
    out_lines.append('    main_ui()')

final_lines = []
in_page_config = False
for line in out_lines:
    if line.startswith('st.set_page_config('):
        final_lines.append('if __name__ == \'__main__\':')
        final_lines.append('    ' + line)
        in_page_config = True
    elif in_page_config and line.startswith('st.markdown("""'):
        final_lines.append('    ' + line)
    elif in_page_config and line == '""", unsafe_allow_html=True)':
        final_lines.append('    ' + line)
        in_page_config = False
    elif in_page_config:
        final_lines.append('    ' + line)
    else:
        final_lines.append(line)

open('app.py', 'w', encoding='utf-8').write('\n'.join(final_lines))
print("app.py patched successfully!")
