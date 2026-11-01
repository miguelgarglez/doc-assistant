import path from "node:path"
import { fileURLToPath } from "node:url"

const src = fileURLToPath(new URL("../src/", import.meta.url))
const features = path.join(src, "features")
const ui = path.join(src, "components", "ui")

function partsWithin(root, target) {
  const relative = path.relative(root, target)
  if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) return null
  return relative ? relative.split(path.sep) : []
}

const rule = {
  meta: {
    type: "problem",
    schema: [],
    messages: {
      privateFeature: "Import another feature through its public index.",
      uiFeature: "Shared UI components cannot import features.",
      dynamic: "Use a literal import path so feature boundaries can be checked.",
    },
  },
  create(context) {
    const filename = context.filename
    const own = partsWithin(features, filename)?.[0]
    const inUi = partsWithin(ui, filename) !== null

    function inspect(node, value) {
      if (typeof value !== "string") {
        if (own || inUi) context.report({ node, messageId: "dynamic" })
        return
      }
      const target = value.startsWith("@/")
        ? path.resolve(src, value.slice(2))
        : value.startsWith(".")
          ? path.resolve(path.dirname(filename), value)
          : null
      if (!target) return
      const parts = partsWithin(features, target)
      if (!parts?.length) return
      if (inUi) {
        context.report({ node, messageId: "uiFeature" })
      } else if (own && own !== parts[0] && parts.length > 1 && !(parts.length === 2 && /^index(?:\.[cm]?[jt]sx?)?$/.test(parts[1]))) {
        context.report({ node, messageId: "privateFeature" })
      }
    }

    return {
      ImportDeclaration(node) { inspect(node.source, node.source.value) },
      ExportNamedDeclaration(node) { if (node.source) inspect(node.source, node.source.value) },
      ExportAllDeclaration(node) { inspect(node.source, node.source.value) },
      ImportExpression(node) { inspect(node.source, node.source.value) },
      CallExpression(node) {
        if (node.callee.type === "Identifier" && node.callee.name === "require") {
          inspect(node, node.arguments[0]?.value)
        }
      },
    }
  },
}

export default rule
