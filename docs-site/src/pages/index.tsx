import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

import styles from './index.module.css';

function HomepageHeader() {
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <h1 className={styles.heroTitle}>
          IntelliView Orchestrator
        </h1>

        <p className={styles.heroSubtitle}>
          API Documentation & Developer Guide
        </p>

        <p className={styles.heroDescription}>
          Explore the IntelliView Orchestrator APIs, endpoints,
          request parameters, responses, and schemas.
        </p>

        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/api">
            API Reference →
          </Link>

          <Link
            className="button button--outline button--lg"
            to="/docs/intro">
            Documentation
          </Link>
        </div>
      </div>
    </header>
  );
}

function FeatureCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="col col--4">
      <div className={styles.featureCard}>
        <div className={styles.featureIcon}>{icon}</div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="IntelliView Orchestrator"
      description="IntelliView Orchestrator API Documentation">

      <HomepageHeader />

      <main>
        <section className={styles.features}>
          <div className="container">
            <div className="row">

              <FeatureCard
                icon="📚"
                title="Complete API Reference"
                description="Browse the available API endpoints with detailed parameters, request bodies, responses, and schemas."
              />

              <FeatureCard
                icon="🔎"
                title="Easy to Navigate"
                description="Explore APIs organized by tags and quickly find the endpoint you need."
              />

              <FeatureCard
                icon="💻"
                title="Developer Friendly"
                description="Use the API documentation to understand integration requirements and build applications faster."
              />

            </div>
          </div>
        </section>

        <section className={styles.apiSection}>
          <div className="container text--center">
            <h2>Explore the IntelliView APIs</h2>

            <p>
              The API reference is generated from the project's
              OpenAPI 3.1 specification.
            </p>

            <p>
              <strong>65 API paths</strong> ·{' '}
              <strong>71 operations</strong> ·{' '}
              <strong>26 schemas</strong>
            </p>

            <Link
              className="button button--primary button--lg"
              to="/docs/api">
              View API Reference
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}