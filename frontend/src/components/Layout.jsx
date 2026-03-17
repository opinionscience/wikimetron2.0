import React from 'react';
import { ArrowRightIcon } from '@heroicons/react/24/solid';
import '../styles/wikimetron.css';

const WIKI_BAROMETER_URL = 'https://wikisensibarometer.disinfo-prompt.eu/';

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
          <a
            href={WIKI_BAROMETER_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="barometer-link barometer-link-header"
            aria-label="Open Wiki Barometer in a new tab"
          >
            <span className="barometer-link-text">Wiki Barometer</span>
            <ArrowRightIcon className="barometer-link-icon" aria-hidden="true" />
          </a>
        </div>
      </div>
    </header>
    <main className="main-content">
      {children}
    </main>
    <footer className="wikimetron-footer">
      <div className="footer-content">
        <a
          href={WIKI_BAROMETER_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="barometer-link barometer-link-footer"
          aria-label="Open Wiki Barometer in a new tab"
        >
          <span className="barometer-link-text">Wiki Barometer</span>
          <ArrowRightIcon className="barometer-link-icon" aria-hidden="true" />
        </a>
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
