/**
 * ESLint rule: max-torchviz3d-per-page
 *
 * Enforces max 2 TorchViz3D or TorchWithHeatmap3D instances per page to prevent
 * WebGL context loss. Each creates a Canvas. Replay/Demo use 2 TorchWithHeatmap3D.
 *
 * Keep max (default 2) in sync with src/constants/webgl.ts MAX_TORCHVIZ3D_PER_PAGE.
 *
 * @see src/constants/webgl.ts
 * @see documentation/WEBGL_CONTEXT_LOSS.md
 */

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'Enforce max 2 TorchViz3D/TorchWithHeatmap3D instances per page to prevent WebGL context loss',
    },
    schema: [{ type: 'integer', minimum: 1 }],
    messages: {
      exceed:
        'Page has {{count}} 3D Canvas instances (TorchViz3D/TorchWithHeatmap3D). Max {{max}} allowed. See constants/webgl.ts and documentation/WEBGL_CONTEXT_LOSS.md.',
    },
  },
  create(context) {
    const max = context.options[0] ?? 2;
    const filename = context.getFilename?.() ?? '';
    const normalized = filename.replace(/\\/g, '/');
    if (normalized.includes('__tests__') || normalized.includes('/app/dev/')) return {};
    if (!/page\.tsx$/.test(normalized) || !normalized.includes('/app/')) return {};
    let count = 0;
    let firstNode = null;
    return {
      JSXElement(node) {
        const open = node.openingElement.name;
        const compName =
          open.type === 'JSXIdentifier'
            ? open.name
            : open.type === 'JSXMemberExpression'
              ? open.property?.name ?? ''
              : '';
        const is3DCanvas =
          compName === 'TorchViz3D' || compName === 'TorchWithHeatmap3D';
        if (is3DCanvas) {
          count++;
          if (!firstNode) firstNode = node;
        }
      },
      'Program:exit'() {
        if (count > max) {
          context.report({
            node: firstNode,
            messageId: 'exceed',
            data: { count, max },
          });
        }
      },
    };
  },
};
