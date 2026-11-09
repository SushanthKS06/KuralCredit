import { Link, NavLink, useNavigate } from "react-router-dom";
import { clearReviewerSession, loadReviewerSession } from "../../lib/auth";
import styles from "./Header.module.css";

interface Props {
  isReviewer: boolean;
}

export function Header({ isReviewer }: Props) {
  const navigate = useNavigate();
  const reviewerSession = loadReviewerSession();

  function handleReviewerLogout() {
    clearReviewerSession();
    navigate("/reviewer/login");
  }

  return (
    <header className={styles.header} role="banner">
      <div className={styles.inner}>
        <Link to="/" className={styles.brand} aria-label="KuralCredit home">
          <span className={styles.brandMark}>KC</span>
          <span className={styles.brandName}>KuralCredit</span>
        </Link>

        <nav className={styles.nav} aria-label="Primary navigation">
          {isReviewer ? (
            <>
              <NavLink
                to="/reviewer"
                end
                className={({ isActive }) =>
                  [styles.navLink, isActive && styles.navLinkActive].filter(Boolean).join(" ")
                }
              >
                Review Queue
              </NavLink>
              {reviewerSession && (
                <button
                  type="button"
                  className={styles.navButton}
                  onClick={handleReviewerLogout}
                >
                  Sign out
                </button>
              )}
            </>
          ) : (
            <>
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  [styles.navLink, isActive && styles.navLinkActive].filter(Boolean).join(" ")
                }
              >
                Apply
              </NavLink>
              <NavLink
                to="/reviewer/login"
                className={({ isActive }) =>
                  [styles.navLink, isActive && styles.navLinkActive].filter(Boolean).join(" ")
                }
              >
                Reviewer
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
