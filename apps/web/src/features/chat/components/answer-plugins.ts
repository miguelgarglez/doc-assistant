import { defaultRehypePlugins } from "streamdown"

import { rehypeFigures } from "@/features/chat/lib/figures"

/** Streamdown replaces its default rehype plugins when it is given a list, so the defaults go first. */
export const answerRehypePlugins = [...Object.values(defaultRehypePlugins), rehypeFigures]
