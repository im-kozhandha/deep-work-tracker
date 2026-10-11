export default function Notice({ notice, onDismiss }) {
  if (!notice) return null;
  const role = notice.type === "error" ? "alert" : "status";
  return (
    <div className={`notice notice-${notice.type}`} role={role}>
      <span>{notice.text}</span>
      <button type="button" className="link-button" onClick={onDismiss} aria-label="Dismiss message">
        ×
      </button>
    </div>
  );
}