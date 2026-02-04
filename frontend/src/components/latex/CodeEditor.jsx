import { useRef, useEffect } from "react";
import Editor from "@monaco-editor/react";

export default function CodeEditor({ value, onChange, language = "latex" }) {
    const editorRef = useRef(null);

    const handleEditorDidMount = (editor, monaco) => {
        editorRef.current = editor;

        // Configure LaTeX language support
        monaco.languages.register({ id: "latex" });

        // Basic LaTeX syntax highlighting
        monaco.languages.setMonarchTokensProvider("latex", {
            tokenizer: {
                root: [
                    [/\\[a-zA-Z]+/, "keyword"],
                    [/\{/, "delimiter.curly"],
                    [/\}/, "delimiter.curly"],
                    [/%.*$/, "comment"],
                    [/\$.*?\$/, "string"],
                ],
            },
        });
    };

    const options = {
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: "on",
        scrollBeyondLastLine: false,
        wordWrap: "on",
        automaticLayout: true,
        tabSize: 2,
        insertSpaces: true,
        renderWhitespace: "selection",
        folding: true,
        lineDecorationsWidth: 10,
        lineNumbersMinChars: 4,
    };

    return (
        <div className="h-full w-full">
            <Editor
                height="100%"
                language={language}
                value={value}
                onChange={onChange}
                onMount={handleEditorDidMount}
                options={options}
                theme="vs-dark"
            />
        </div>
    );
}
