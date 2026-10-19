const json = (r) => (r.ok ? r.json() : r.json().then((e) => Promise.reject(new Error(e.detail || "Request failed"))));
const post = (url, body) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(json);

export const sendChat = (thread_id, message) => post("/api/chat", { thread_id, message });
export const approve = (thread_id, approved) => post("/api/approve", { thread_id, approved });
export const listBooks = () => fetch("/api/books").then(json);
export const deleteBook = (name) => fetch(`/api/books/${encodeURIComponent(name)}`, { method: "DELETE" }).then(json);
export const uploadBooks = (files) => {
  const fd = new FormData();
  [...files].forEach((f) => fd.append("files", f));
  return fetch("/api/upload", { method: "POST", body: fd }).then(json);
};
export const fileUrl = (name) => `/api/files/${encodeURIComponent(name)}`;
export const listChats = () => fetch("/api/chats").then(json);
export const getChat = (id) => fetch(`/api/chats/${encodeURIComponent(id)}`).then(json);
export const deleteChat = (id) => fetch(`/api/chats/${encodeURIComponent(id)}`, { method: "DELETE" }).then(json);
