import { STATUS_HINTS, STATUS_LABELS } from "../constants";

export default function StatusBadge({ status }) {
  return (
    <span className={`badge badge-${status}`} title={STATUS_HINTS[status] ?? ""}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}