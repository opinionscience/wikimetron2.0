import React from 'react';
import '../styles/wikimetron.css';

const Layout = ({ children, pageTitle, subtitle, onBackToConfig }) => (
  <div className="wikimetron-app">
    <header className="wikimetron-header minimal-header">
      <div className="minimal-container">
        <div className="header-content-principal">
          <a
            href="https://disinfo-prompt.eu/"
            target="_blank"
            rel="noopener noreferrer"
            className="header-logo-link"
          >
            <img
              src="/prompt.png"
              alt="Logo 1"
              className="header-logo"
            />
          </a>
          <h1 className="minimal-title">Wikipedia Sensitivity Meter</h1>
        </div>
      </div>
    </header>
    <main className="main-content">
      {children}
    </main>
    <footer className="wikimetron-footer">
      <div className="footer-content">
        <div className="footer-logos">
          <a
            href="https://www.opsci.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-logo-link"
          >
            <img
              src="/opsci-logo-hw.png"
              alt="Logo 1"
              className="footer-logo"
            />
          </a>
          <a
            href="https://www.wikimedia.fr/"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-logo-link"
          >
            <img
              src="/Wikimedia_France_logo_-_horizontal_-_white.svg.png"
              alt="Logo 2"
              className="footer-logo footer-logo-2"
            />
          </a>
        </div>
        <p>
          The PROMPT project has received funding from the European Commission under grant agreement CNECT/LC-02629302.
        </p>
        <div className="footer-eu">
          <img
            src="/cofunded_by_eu.png"
            alt="Co-funded by the European Union"
            className="eu-logo"
          />
        </div>
      </div>
    </footer>
  </div>
);

export default Layout;