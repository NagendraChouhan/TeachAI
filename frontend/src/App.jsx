import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { approve, deleteBook, deleteChat, fileUrl, getChat, listBooks, listChats, sendChat, uploadBooks } from "./api";

const newThread = () => crypto.randomUUID();
const LAST = "teachai:lastChat";
const remember = (id) => { try { localStorage.setItem(LAST, id); } catch {} };
const recall = () => { try { return localStorage.getItem(LAST); } catch { return null; } };

const SUGGESTIONS = [
  { icon: "💡", title: "Ask a question", text: "Explain <topic> from my book in simple words" },
  { icon: "🎞️", title: "Make a PPT", text: "Make an 8 slide ppt on <topic>" },
  { icon: "📖", title: "Reading material", text: "Make reading material from the last ppt" },
  { icon: "📝", title: "Quiz paper", text: "Make a quiz of 10 questions" },
  { icon: "✉️", title: "Email students", text: "Send mail to students that class is tomorrow at 10 am" },
  { icon: "📎", title: "Email a file", text: "Email the reading material to students" },
];

const fileKind = (n) => (n.endsWith(".pptx") ? ["PPT", "ppt"] : n.includes("quiz") ? ["Quiz", "quiz"] : ["PDF", "pdf"]);

function Avatar({ role }) {
  return <div className={`avatar ${role}`}>{role === "bot" ? "🎓" : "🧑‍🏫"}</div>;
}

function FileCard({ name }) {
  const [label, kind] = fileKind(name);
  return (
    <a className={`filecard ${kind}`} href={fileUrl(name)}>
      <span className="ficon">{kind === "ppt" ? "📊" : kind === "quiz" ? "📝" : "📄"}</span>
      <span className="finfo">
        <b>{name}</b>
        <small>{label} · click to download</small>
      </span>
      <span className="fdl">⬇</span>
    </a>
  );
}

function Approval({ data, onDecide }) {
  return (
    <div className="approval">
      <div className="ahead">✉️ Review email before sending</div>
      <div className="arow"><span>To</span><b>{data.to.join(", ")}</b></div>
      <div className="arow"><span>Subject</span><b>{data.subject}</b></div>
      <div className="arow"><span>Attachment</span><b>{data.attachment || "none"}</b></div>
      <pre>{data.body}</pre>
      <div className="abtns">
        <button className="ok" onClick={() => onDecide(true)}>✓ Approve & send</button>
        <button className="no" onClick={() => onDecide(false)}>Cancel</button>
      </div>
    </div>
  );
}

export default function App() {
  const [threadId, setThreadId] = useState(() => recall() || newThread());
  const [chats, setChats] = useState([]);
  const [books, setBooks] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [menu, setMenu] = useState(false);
  const endRef = useRef();

  const refreshBooks = () => listBooks().then(setBooks).catch(() => {});
  const refreshChats = () => listChats().then(setChats).catch(() => {});
  const open = (id) => {
    setThreadId(id); remember(id); setMenu(false);
    getChat(id).then(setMsgs).catch(() => setMsgs([]));
  };
  useEffect(() => { refreshBooks(); refreshChats(); getChat(threadId).then(setMsgs).catch(() => {}); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const addBot = (r) => setMsgs((m) => [...m, { role: "bot", text: r.reply, files: r.files, approval: r.approval }]);
  const fail = (e) => setMsgs((m) => [...m, { role: "bot", text: `⚠️ ${e.message}` }]);

  const send = async (text) => {
    if (!text.trim() || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setBusy(true);
    remember(threadId);
    try { addBot(await sendChat(threadId, text)); } catch (e) { fail(e); }
    setBusy(false);
    refreshChats();
  };

  const decide = async (idx, ok) => {
    setMsgs((m) => m.map((x, i) => (i === idx ? { ...x, approval: null, text: x.text + (ok ? "" : "") } : x)));
    setBusy(true);
    try { addBot(await approve(threadId, ok)); } catch (e) { fail(e); }
    setBusy(false);
  };

  const onUpload = async (e) => {
    if (!e.target.files.length) return;
    setUploading(true);
    try { await uploadBooks(e.target.files); await refreshBooks(); } catch (err) { fail(err); }
    setUploading(false);
    e.target.value = "";
  };

  const reset = () => { const id = newThread(); setMsgs([]); setThreadId(id); remember(id); setMenu(false); };
  const removeChat = async (e, id) => {
    e.stopPropagation();
    await deleteChat(id).catch(() => {});
    if (id === threadId) reset();
    refreshChats();
  };
  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } };

  return (
    <div className="app">
      <aside className={menu ? "open" : ""}>
        <div className="brand" onClick={reset} title="Go to home" role="button">
          <span className="logo">🎓</span><div><h1>TeachAI</h1><small>Your teaching assistant</small></div>
        </div>
        <button className="newchat" onClick={reset}>＋ New chat</button>

        <div className="sect">Chat history</div>
        <ul className="chats">
          {chats.map((c) => (
            <li key={c.id} className={c.id === threadId ? "active" : ""} onClick={() => open(c.id)} title={c.title}>
              <span className="cicon">💬</span><span className="cname">{c.title}</span>
              <button title="Delete chat" onClick={(e) => removeChat(e, c.id)}>✕</button>
            </li>
          ))}
          {!chats.length && <li className="empty">No chats yet</li>}
        </ul>

        <div className="sect">Your books</div>
        <label className={`upload ${uploading ? "busy" : ""}`}>
          <span className="uicon">{uploading ? "⏳" : "📤"}</span>
          <b>{uploading ? "Reading your book…" : "Upload PDF / TXT"}</b>
          <small>{uploading ? "first time can take a minute" : "books & study material"}</small>
          <input type="file" multiple accept=".pdf,.txt,.md" onChange={onUpload} hidden disabled={uploading} />
        </label>
        <ul className="books">
          {books.map((b) => (
            <li key={b}>
              <span className="bicon">📘</span><span className="bname" title={b}>{b}</span>
              <button title="Remove" onClick={() => deleteBook(b).then(refreshBooks)}>✕</button>
            </li>
          ))}
          {!books.length && <li className="empty">No books yet</li>}
        </ul>
        <div className="foot">PPT, reading material & quiz use your books first, then the web if needed.</div>
      </aside>

      <main>
        <header>
          <button className="burger" onClick={() => setMenu(!menu)}>☰</button>
          <div><b>Class assistant</b><small>{books.length} book{books.length === 1 ? "" : "s"} loaded</small></div>
        </header>

        <div className="chat">
          {!msgs.length && (
            <div className="welcome">
              <div className="hero">🎓</div>
              <h2>What would you like to prepare today?</h2>
              <p>Upload your books, then ask me to explain topics or create class material.</p>
              <div className="cards">
                {SUGGESTIONS.map((s) => (
                  <button key={s.title} onClick={() => setInput(s.text)}>
                    <span>{s.icon}</span><b>{s.title}</b><small>{s.text}</small>
                  </button>
                ))}
              </div>
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`row ${m.role}`}>
              <Avatar role={m.role} />
              <div className={`bubble ${m.role}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                {m.files?.map((f) => <FileCard key={f} name={f} />)}
                {m.approval && <Approval data={m.approval} onDecide={(ok) => decide(i, ok)} />}
              </div>
            </div>
          ))}
          {busy && (
            <div className="row bot">
              <Avatar role="bot" />
              <div className="bubble bot typing"><i /><i /><i /><small>Working on it… slides & PDFs with images can take up to a minute</small></div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="composer">
          <textarea rows={1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey}
            placeholder="Ask a question, or request a ppt, reading material, quiz or email…" />
          <button disabled={busy || !input.trim()} onClick={() => send(input)}>➤</button>
        </div>
      </main>
    </div>
  );
}
