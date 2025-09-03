import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">
          {siteConfig.tagline}
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Open Documentation
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`Docs | ${siteConfig.title}`}
      description="MCP server for Microsoft To Do (clean architecture)">
      <HomepageHeader />
      <main>
        <section className="container">
          <div className="row">
            <div className="col col--12">
              <h2>About</h2>
              <p>
                Cleanly layered MCP server that exposes Microsoft To Do over JSON-RPC (initialize, tools/list, tools/call).
                Authentication is handled by an external helper; only the access token is shared via a read-only secrets volume.
              </p>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
