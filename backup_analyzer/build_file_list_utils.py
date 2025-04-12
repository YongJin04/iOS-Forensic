import os
from typing import Dict, Any
from tkinter import ttk

def build_file_list_tree(
    file_list_tree: "ttk.Treeview",
    sub_dict: Dict[str, Any],
    parent: str = "",
    full_path: str = "",
    current_depth: int = 0,
    max_depth: int = 1,
) -> None:
    """#0(text) = 마지막 이름, values[0] = 전체 경로(숨김 열)."""
    if current_depth == 0:
        for item in file_list_tree.get_children():
            file_list_tree.delete(item)

    if not sub_dict:
        return

    for name, child_obj in sorted(sub_dict.items()):
        if not name:
            continue

        node_full_path = f"{full_path}/{name}" if full_path else name
        display_name   = node_full_path.split('/')[-1]

        # values: (fullpath, size, type, mdate, cdate, perm)
        values = (node_full_path, ' ', ' ', ' ', ' ', ' ')

        node_id = file_list_tree.insert(
            parent,
            'end',
            text=display_name,
            values=values,
        )

        if isinstance(child_obj, dict) and current_depth + 1 < max_depth:
            build_file_list_tree(
                file_list_tree,
                child_obj,
                parent=node_id,
                full_path=node_full_path,
                current_depth=current_depth + 1,
                max_depth=max_depth,
            )
