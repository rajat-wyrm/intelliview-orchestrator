'use client'; // Error boundaries must be Client Components

import React, { useEffect } from 'react';
import Link from 'next/link';

export default function Error({ error, reset }) {
  useEffect(() => {
    // Log the error securely to the console for internal debugging
    console.error('Application Error Boundary caught:', error);
  }, [error]);

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.iconContainer}>
          <span style={styles.icon}>⚠️</span>
        </div>
        
        <h2 style={styles.heading}>Something went wrong</h2>
        
        <p style={styles.message}>
          An unexpected error occurred while processing your request. Please try again or return to the main dashboard.
        </p>

        <div style={styles.buttonGroup}>
          <button onClick={() => reset()} style={styles.retryButton}>
            Try Again
          </button>
          
          <Link href="/" style={styles.homeLink}>
            Go Back Home
          </Link>
        </div>
      </div>
    </div>
  );
}

// Inline responsive styling keeping modifications fully isolated to this file
const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '80vh',
    padding: '20px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    backgroundColor: '#f9fafb',
  },
  card: {
    maxWidth: '450px',
    width: '100%',
    backgroundColor: '#ffffff',
    padding: '40px 32px',
    borderRadius: '12px',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    textAlign: 'center',
  },
  iconContainer: {
    marginBottom: '20px',
  },
  icon: {
    fontSize: '48px',
  },
  heading: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#111827',
    marginBottom: '12px',
  },
  message: {
    fontSize: '15px',
    color: '#4b5563',
    lineHeight: '1.5',
    marginBottom: '32px',
  },
  buttonGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  retryButton: {
    padding: '12px 24px',
    fontSize: '15px',
    fontWeight: '600',
    color: '#ffffff',
    backgroundColor: '#2563eb',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  homeLink: {
    padding: '12px 24px',
    fontSize: '15px',
    fontWeight: '600',
    color: '#4b5563',
    backgroundColor: '#f3f4f6',
    borderRadius: '6px',
    textDecoration: 'none',
    textAlign: 'center',
    transition: 'background-color 0.2s',
  },
};
