import { Outlet, useLocation } from "react-router-dom";
import { Header } from "./Header";
import styles from "./AppShell.module.css";

export function AppShell() {
  const { pathname } = useLocation();
  const isReviewer = pathname.startsWith("/reviewer");

  return (
    <div className={styles.shell}>
      <Header isReviewer={isReviewer} />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
