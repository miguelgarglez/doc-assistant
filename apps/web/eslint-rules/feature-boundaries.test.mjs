import path from "node:path"
import { fileURLToPath } from "node:url"
import { RuleTester } from "eslint"
import rule from "./feature-boundaries.mjs"

const src = fileURLToPath(new URL("../src/", import.meta.url))
const chat = path.join(src, "features/chat/view.js")
const ui = path.join(src, "components/ui/button.js")
const cases = new RuleTester({ languageOptions: { ecmaVersion: "latest", sourceType: "module" } })
cases.run("feature-boundaries", rule, {
  valid: [
    { filename: chat, code: 'import x from "./private"' },
    { filename: chat, code: 'import x from "@/features/viewer"' },
    { filename: chat, code: 'import x from "../viewer/index"' },
    { filename: chat, code: 'import x from "@/components/ui/button"' },
  ],
  invalid: [
    { filename: chat, code: 'import x from "@/features/viewer/private"', errors: [{ messageId: "privateFeature" }] },
    { filename: chat, code: 'export * from "../viewer/private"', errors: [{ messageId: "privateFeature" }] },
    { filename: chat, code: 'require("../viewer/private")', errors: [{ messageId: "privateFeature" }] },
    { filename: chat, code: 'import(name)', errors: [{ messageId: "dynamic" }] },
    { filename: ui, code: 'import x from "@/features/viewer"', errors: [{ messageId: "uiFeature" }] },
  ],
})
