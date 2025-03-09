from collections import defaultdict

def build_file_tree_and_map(file_info_list):
    """백업 파일 리스트를 트리 구조로 변환하는 함수"""
    tree = defaultdict(dict)
    path_map = {}

    for fileID, domain, rel_path, flags in file_info_list:
        parts = rel_path.strip("/").split("/")
        current_level = tree[domain]
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                current_level = current_level.setdefault(part, {})
            else:
                current_level[part] = {}

    return dict(tree), path_map
