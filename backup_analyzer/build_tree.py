from collections import defaultdict


def build_tree(file_info_list):
    """ Converts the backup file list into a tree structure. """
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


def build_backup_tree(tree_widget, file_tree, icon_dict=None):
    """ Builds the backup file tree structure in the UI, excluding the last leaf nodes. """
    path_dict = {}
    backup_tree_nodes = {}

    # Clear the existing tree
    tree_widget.delete(*tree_widget.get_children())

    # Create root nodes for different file categories (아이콘 추가)
    system_node = tree_widget.insert("", "end", text=" System Files", 
                                    image=icon_dict['folder'] if icon_dict else "")
    user_app_node = tree_widget.insert("", "end", text=" User App Files", 
                                     image=icon_dict['folder'] if icon_dict else "")
    app_group_node = tree_widget.insert("", "end", text=" App Group Files", 
                                      image=icon_dict['folder'] if icon_dict else "")
    app_plugin_node = tree_widget.insert("", "end", text=" App Plugin Files", 
                                       image=icon_dict['folder'] if icon_dict else "")
    
    
    def get_file_icon(name):
        """파일 확장자에 따라 적절한 아이콘을 반환"""
        if not icon_dict:
            return ""
        if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            return icon_dict["image"]
        else:
            return icon_dict["file"]
        

    def insert_tree(parent, current_dict, current_path=""):
        """ Recursively inserts directories and files into the tree widget. """
        path_dict[current_path] = current_dict
        for name, child_obj in sorted(current_dict.items()):
            if not name:
                continue
            
            # Check if the child is a dict and contains further subdirectories
            subdirs = {k: v for k, v in child_obj.items() if k and isinstance(v, dict)}
            
            # Only insert if there are subdirectories or the path is not a final leaf node
            if subdirs or (current_path and not all(isinstance(v, dict) and not v for v in child_obj.values())):
                new_path = (current_path + "/" + name).strip("/")
                
                # Insert as a folder if it has subdirectories
                if subdirs:
                    node_id = tree_widget.insert(parent, "end", text=" " + name, 
                                               values=(new_path,), 
                                               image=icon_dict['folder'] if icon_dict else "")
                    backup_tree_nodes[new_path] = node_id
                    insert_tree(node_id, child_obj, new_path)
                # If no subdirs, but not a final leaf, insert as a node
                else:
                    node_id = tree_widget.insert(parent, "end", text=" " + name, 
                                              values=(new_path,), 
                                              image=get_file_icon(name))
                    backup_tree_nodes[new_path] = node_id

    # Categorize and insert file domains into the respective nodes
    for domain, sub_dict in sorted(file_tree.items()):
        if "AppDomainGroup" in domain:
            insert_tree(app_group_node, {domain: sub_dict}, domain)
        elif "AppDomainPlugin" in domain:
            insert_tree(app_plugin_node, {domain: sub_dict}, domain)
        elif "HomeDomain" in domain or "AppDomain-" in domain:
            insert_tree(user_app_node, {domain: sub_dict}, domain)
        else:
            insert_tree(system_node, {domain: sub_dict}, domain)

    return path_dict, backup_tree_nodes