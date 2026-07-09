import type { TreeOption, TreeOverrideNodeClickBehaviorReturn } from 'naive-ui';

type AuthTreeNode = {
  key: string;
  isParent: boolean;
  resourceId: string | null;
  disabled?: boolean;
  checkboxDisabled?: boolean;
  children?: AuthTreeNode[];
};

export function collectLeafIdSet(nodes: AuthTreeNode[]) {
  const ids = new Set<string>();

  nodes.forEach(node => {
    const children = node.children || [];
    if (children.length) {
      collectLeafIdSet(children).forEach(id => ids.add(id));
    } else if (!node.disabled && !node.isParent && node.resourceId) {
      ids.add(node.resourceId);
    }
  });

  return ids;
}

export function getCheckedKeysByResourceIds(resourceIds: string[], tree: AuthTreeNode[]) {
  const resourceIdSet = new Set(resourceIds);
  const checkedKeys: string[] = [];

  function walk(nodes: AuthTreeNode[]) {
    nodes.forEach(node => {
      if (!node.isParent && node.resourceId && resourceIdSet.has(node.resourceId)) {
        checkedKeys.push(node.key);
      }
      walk(node.children || []);
    });
  }

  walk(tree);

  return checkedKeys;
}

export function getResourceIdByKey(key: string, tree: AuthTreeNode[]): string | null {
  let resourceId: string | null = null;

  function walk(nodes: AuthTreeNode[]) {
    nodes.some(node => {
      if (node.key === key) {
        resourceId = node.resourceId;
        return true;
      }
      walk(node.children || []);
      return resourceId !== null;
    });
  }

  walk(tree);

  return resourceId;
}

function collectLeafIdsByKey(key: string, tree: AuthTreeNode[]) {
  const ids: string[] = [];

  function collectLeaves(node: AuthTreeNode) {
    const children = node.children || [];
    if (children.length) {
      children.forEach(collectLeaves);
      return;
    }
    if (!node.disabled && !node.isParent && node.resourceId) {
      ids.push(node.resourceId);
    }
  }

  function walk(nodes: AuthTreeNode[]): boolean {
    return nodes.some(node => {
      if (node.key === key) {
        collectLeaves(node);
        return true;
      }
      return walk(node.children || []);
    });
  }

  walk(tree);

  return ids;
}

export function getCheckedLeafIds(checkedKeys: string[], tree: AuthTreeNode[], requiredIds: string[] = []) {
  const leafIdSet = collectLeafIdSet(tree);
  const checkedIds = checkedKeys.flatMap(key => collectLeafIdsByKey(key, tree));

  return Array.from(new Set([...checkedIds, ...requiredIds].map(String).filter(id => leafIdSet.has(id))));
}

export function enhanceAuthTreeNodes<T extends AuthTreeNode>(nodes: T[]): T[] {
  return nodes.map(node => {
    const children = enhanceAuthTreeNodes((node.children || []) as T[]);
    const enhancedNode: T = {
      ...node,
      checkboxDisabled: node.disabled
    };

    if (children.length) {
      enhancedNode.children = children;
    } else {
      delete enhancedNode.children;
    }

    return enhancedNode;
  });
}

export function overrideAuthTreeNodeClickBehavior({
  option
}: {
  option: TreeOption;
}): TreeOverrideNodeClickBehaviorReturn {
  if (option.children?.length || option.isParent) {
    return 'toggleExpand';
  }

  if (option.disabled || option.checkboxDisabled) {
    return 'none';
  }

  return 'toggleCheck';
}
