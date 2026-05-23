#!/usr/bin/env python3
"""
自动生成案件关系图脚本
从 Obsidian 案件笔记中提取信息，生成 Excalidraw 关系图 JSON 文件
用法：python auto_diagram.py <案件笔记路径> [输出路径]
"""

import sys
import os
import json
import yaml
import re
from pathlib import Path

def extract_frontmatter(content):
    """提取 YAML frontmatter"""
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            pass
    return {}

def extract_parties(content):
    """从内容中提取当事人信息"""
    parties = []
    # 查找原告、被告信息
    for line in content.split('\n'):
        if '原告' in line or '被告' in line:
            parties.append(line.strip())
    return parties

def extract_evidence(content):
    """提取证据清单"""
    evidence = []
    in_evidence_section = False
    for line in content.split('\n'):
        if line.startswith('## 证据清单'):
            in_evidence_section = True
            continue
        if in_evidence_section and line.startswith('## '):
            break
        if in_evidence_section and ('**证据' in line or '|' in line or '- **证据' in line):
            evidence.append(line.strip())
    return evidence

def create_excalidraw_elements(frontmatter, parties, evidence):
    """创建 Excalidraw 元素"""
    elements = []
    
    # 案件标题
    elements.append({
        "type": "text",
        "version": 1,
        "versionNonce": 1,
        "isDeleted": false,
        "id": "title",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 300,
        "y": 50,
        "strokeColor": "#000000",
        "backgroundColor": "#ffffff",
        "width": 400,
        "height": 50,
        "seed": 1001,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [],
        "updated": 1745862900000,
        "link": null,
        "locked": false,
        "fontSize": 32,
        "fontFamily": 1,
        "text": frontmatter.get('案件名称', frontmatter.get('案由', '案件关系图')),
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": null,
        "originalText": frontmatter.get('案件名称', frontmatter.get('案由', '案件关系图')),
        "lineHeight": 1.25
    })
    
    # 原告节点
    plaintiff_name = frontmatter.get('客户', '原告')
    elements.append({
        "type": "rectangle",
        "version": 1,
        "versionNonce": 2,
        "isDeleted": false,
        "id": "plaintiff",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 100,
        "y": 150,
        "strokeColor": "#1864ab",
        "backgroundColor": "#a5d8ff",
        "width": 180,
        "height": 80,
        "seed": 1002,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [
            {
                "type": "text",
                "id": "plaintiff_label"
            }
        ],
        "updated": 1745862900000,
        "link": null,
        "locked": false
    })
    
    elements.append({
        "type": "text",
        "version": 1,
        "versionNonce": 3,
        "isDeleted": false,
        "id": "plaintiff_label",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 110,
        "y": 170,
        "strokeColor": "#1864ab",
        "backgroundColor": "#a5d8ff",
        "width": 160,
        "height": 40,
        "seed": 1003,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [],
        "updated": 1745862900000,
        "link": null,
        "locked": false,
        "fontSize": 24,
        "fontFamily": 1,
        "text": f"原告\n{plaintiff_name}",
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": "plaintiff",
        "originalText": f"原告\n{plaintiff_name}",
        "lineHeight": 1.25
    })
    
    # 被告节点
    defendant_name = frontmatter.get('对方当事人', '被告')
    elements.append({
        "type": "rectangle",
        "version": 1,
        "versionNonce": 4,
        "isDeleted": false,
        "id": "defendant",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 400,
        "y": 150,
        "strokeColor": "#c92a2a",
        "backgroundColor": "#ffc9c9",
        "width": 180,
        "height": 80,
        "seed": 1004,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [
            {
                "type": "text",
                "id": "defendant_label"
            }
        ],
        "updated": 1745862900000,
        "link": null,
        "locked": false
    })
    
    elements.append({
        "type": "text",
        "version": 1,
        "versionNonce": 5,
        "isDeleted": false,
        "id": "defendant_label",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 410,
        "y": 170,
        "strokeColor": "#c92a2a",
        "backgroundColor": "#ffc9c9",
        "width": 160,
        "height": 40,
        "seed": 1005,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [],
        "updated": 1745862900000,
        "link": null,
        "locked": false,
        "fontSize": 24,
        "fontFamily": 1,
        "text": f"被告\n{defendant_name}",
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": "defendant",
        "originalText": f"被告\n{defendant_name}",
        "lineHeight": 1.25
    })
    
    # 案件事实节点
    elements.append({
        "type": "diamond",
        "version": 1,
        "versionNonce": 6,
        "isDeleted": false,
        "id": "case_fact",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 250,
        "y": 300,
        "strokeColor": "#5c940d",
        "backgroundColor": "#d8f5a2",
        "width": 180,
        "height": 100,
        "seed": 1006,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [
            {
                "type": "text",
                "id": "case_fact_label"
            }
        ],
        "updated": 1745862900000,
        "link": null,
        "locked": false
    })
    
    case_type = frontmatter.get('案件类型', frontmatter.get('案由', '案件事实'))
    elements.append({
        "type": "text",
        "version": 1,
        "versionNonce": 7,
        "isDeleted": false,
        "id": "case_fact_label",
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 260,
        "y": 330,
        "strokeColor": "#5c940d",
        "backgroundColor": "#d8f5a2",
        "width": 160,
        "height": 40,
        "seed": 1007,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [],
        "updated": 1745862900000,
        "link": null,
        "locked": false,
        "fontSize": 20,
        "fontFamily": 1,
        "text": case_type,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": "case_fact",
        "originalText": case_type,
        "lineHeight": 1.25
    })
    
    # 连接箭头
    elements.append({
        "type": "arrow",
        "version": 1,
        "versionNonce": 8,
        "isDeleted": false,
        "id": "arrow1",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 280,
        "y": 230,
        "strokeColor": "#1864ab",
        "backgroundColor": "#a5d8ff",
        "width": 0,
        "height": 70,
        "seed": 1008,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [],
        "updated": 1745862900000,
        "link": null,
        "locked": false,
        "points": [
            [0, 0],
            [0, 70]
        ],
        "lastCommittedPoint": null,
        "startBinding": {
            "elementId": "plaintiff",
            "focus": 0,
            "gap": 1
        },
        "endBinding": {
            "elementId": "case_fact",
            "focus": -0.1,
            "gap": 1
        },
        "startArrowhead": null,
        "endArrowhead": "arrow"
    })
    
    elements.append({
        "type": "arrow",
        "version": 1,
        "versionNonce": 9,
        "isDeleted": false,
        "id": "arrow2",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": 380,
        "y": 230,
        "strokeColor": "#c92a2a",
        "backgroundColor": "#ffc9c9",
        "width": 0,
        "height": 70,
        "seed": 1009,
        "groupIds": [],
        "frameId": null,
        "roundness": null,
        "boundElements": [],
        "updated": 1745862900000,
        "link": null,
        "locked": false,
        "points": [
            [0, 0],
            [0, 70]
        ],
        "lastCommittedPoint": null,
        "startBinding": {
            "elementId": "defendant",
            "focus": 0,
            "gap": 1
        },
        "endBinding": {
            "elementId": "case_fact",
            "focus": 0.1,
            "gap": 1
        },
        "startArrowhead": null,
        "endArrowhead": "arrow"
    })
    
    # 证据节点（最多3个）
    for i, ev in enumerate(evidence[:3]):
        x_pos = 100 + i * 200
        ev_id = f"evidence_{i}"
        ev_label_id = f"evidence_label_{i}"
        
        elements.append({
            "type": "ellipse",
            "version": 1,
            "versionNonce": 10 + i,
            "isDeleted": false,
            "id": ev_id,
            "fillStyle": "hachure",
            "strokeWidth": 1,
            "strokeStyle": "dashed",
            "roughness": 1,
            "opacity": 100,
            "angle": 0,
            "x": x_pos,
            "y": 450,
            "strokeColor": "#495057",
            "backgroundColor": "#f8f9fa",
            "width": 150,
            "height": 80,
            "seed": 1010 + i,
            "groupIds": [],
            "frameId": null,
            "roundness": null,
            "boundElements": [
                {
                    "type": "text",
                    "id": ev_label_id
                }
            ],
            "updated": 1745862900000,
            "link": null,
            "locked": false
        })
        
        # 简化证据文本
        ev_text = ev[:20] + "..." if len(ev) > 20 else ev
        elements.append({
            "type": "text",
            "version": 1,
            "versionNonce": 20 + i,
            "isDeleted": false,
            "id": ev_label_id,
            "fillStyle": "hachure",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "angle": 0,
            "x": x_pos + 10,
            "y": 470,
            "strokeColor": "#495057",
            "backgroundColor": "#f8f9fa",
            "width": 130,
            "height": 40,
            "seed": 1020 + i,
            "groupIds": [],
            "frameId": null,
            "roundness": null,
            "boundElements": [],
            "updated": 1745862900000,
            "link": null,
            "locked": false,
            "fontSize": 14,
            "fontFamily": 1,
            "text": f"证据{i+1}\n{ev_text}",
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": ev_id,
            "originalText": f"证据{i+1}\n{ev_text}",
            "lineHeight": 1.25
        })
        
        # 连接箭头
        elements.append({
            "type": "arrow",
            "version": 1,
            "versionNonce": 30 + i,
            "isDeleted": false,
            "id": f"arrow_ev_{i}",
            "fillStyle": "hachure",
            "strokeWidth": 1,
            "strokeStyle": "dashed",
            "roughness": 1,
            "opacity": 100,
            "angle": 0,
            "x": x_pos + 75,
            "y": 430,
            "strokeColor": "#495057",
            "backgroundColor": "#f8f9fa",
            "width": 0,
            "height": 20,
            "seed": 1030 + i,
            "groupIds": [],
            "frameId": null,
            "roundness": null,
            "boundElements": [],
            "updated": 1745862900000,
            "link": null,
            "locked": false,
            "points": [
                [0, 0],
                [0, 20]
            ],
            "lastCommittedPoint": null,
            "startBinding": {
                "elementId": "case_fact",
                "focus": -0.5 + i * 0.5,
                "gap": 1
            },
            "endBinding": {
                "elementId": ev_id,
                "focus": 0,
                "gap": 1
            },
            "startArrowhead": null,
            "endArrowhead": "triangle"
        })
    
    return elements

def main():
    if len(sys.argv) < 2:
        print("用法：python auto_diagram.py <案件笔记路径> [输出路径]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        # 默认输出到同目录，扩展名为 .excalidraw
        stem = Path(input_path).stem
        output_path = str(Path(input_path).with_name(f"{stem}-关系图.excalidraw"))
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = extract_frontmatter(content)
        parties = extract_parties(content)
        evidence = extract_evidence(content)
        
        elements = create_excalidraw_elements(frontmatter, parties, evidence)
        
        excalidraw_data = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": elements,
            "appState": {
                "viewBackgroundColor": "#ffffff",
                "gridSize": null,
                "currentItemStrokeColor": "#1864ab",
                "currentItemBackgroundColor": "#a5d8ff",
                "currentItemFillStyle": "hachure",
                "currentItemStrokeWidth": 2,
                "currentItemStrokeStyle": "solid",
                "currentItemRoughness": 1,
                "currentItemOpacity": 100,
                "currentItemFontFamily": 1,
                "currentItemFontSize": 24,
                "currentItemTextAlign": "center",
                "currentItemStrokeSharpness": "sharp",
                "currentItemStartArrowhead": null,
                "currentItemEndArrowhead": "arrow",
                "currentItemLinearStrokeSharpness": "round",
                "exportWithDarkMode": false
            },
            "files": {}
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(excalidraw_data, f, ensure_ascii=False, indent=2)
        
        print(f"关系图已生成：{output_path}")
        print(f"包含 {len(elements)} 个元素")
        
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()