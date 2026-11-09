import { useState } from "react";
import { Link } from "react-router-dom";
import type { ReviewerQueueItem } from "../../api/types";
import { formatDate } from "../../lib/format";
import { Button } from "../common/Button";
import { StatusBadge } from "../common/StatusBadge";
import styles from "./ReviewQueue.module.css";

interface Props {
  items: ReviewerQueueItem[];
  total: number;
  loading?: boolean;
}

export function ReviewQueue({ items, total, loading = false }: Props) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = items.filter((item) => {
    const matchesSearch =
      !search ||
      item.applicant_name.toLowerCase().includes(search.toLowerCase()) ||
      item.business_name.toLowerCase().includes(search.toLowerCase()) ||
      item.reference.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || item.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className={styles.container} role="region" aria-label="Reviewer Queue">
      <div className={styles.filtersRow}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search by Reference, Applicant or Business name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className={styles.filterSelect}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All Statuses ({total})</option>
          <option value="submitted_for_human_review">Submitted for Review</option>
          <option value="human_review_in_progress">Review in Progress</option>
          <option value="needs_more_information">Needs More Information</option>
          <option value="review_completed">Review Completed</option>
        </select>
      </div>

      <div className={styles.tableCard}>
        {filtered.length === 0 ? (
          <div className={styles.empty}>
            {loading ? "Loading applications..." : "No applications found matching your criteria."}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Reference No</th>
                <th className={styles.th}>Applicant</th>
                <th className={styles.th}>Business Name</th>
                <th className={styles.th}>Completeness</th>
                <th className={styles.th}>Submitted Date</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.application_id}>
                  <td className={styles.td}>
                    <span className={styles.refNo}>{item.reference}</span>
                  </td>
                  <td className={styles.td}>
                    <strong>{item.applicant_name}</strong>
                  </td>
                  <td className={styles.td}>{item.business_name}</td>
                  <td className={styles.td}>
                    <span style={{ fontWeight: 600 }}>{item.completeness_percent}%</span>
                  </td>
                  <td className={styles.td}>{formatDate(item.created_at)}</td>
                  <td className={styles.td}>
                    <StatusBadge status={item.status} />
                  </td>
                  <td className={styles.td}>
                    <Link to={`/reviewer/${item.application_id}`}>
                      <Button size="sm" variant="secondary">
                        Open Review
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
