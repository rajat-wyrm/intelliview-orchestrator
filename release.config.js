module.exports = {
  branches: ['main'],
  tagFormat: 'v${version}',
  repositoryUrl: 'https://github.com/rajat-wyrm/intelliview-orchestrator.git',
  plugins: [
    [
      '@semantic-release/commit-analyzer',
      {
        preset: 'angular',
        releaseRules: [
          { type: 'feat', release: 'minor' },
          { type: 'fix', release: 'patch' },
          { type: 'perf', release: 'patch' },
          { type: 'revert', release: 'patch' },
          { breaking: true, release: 'major' },
          { type: 'docs', release: false },
          { type: 'style', release: false },
          { type: 'refactor', release: false },
          { type: 'test', release: false },
          { type: 'chore', release: false },
          { type: 'ci', release: false },
          { type: 'build', release: false }
        ],
        parserOpts: {
          noteKeywords: ['BREAKING CHANGE', 'BREAKING-CHANGE']
        }
      }
    ],
    [
      '@semantic-release/release-notes-generator',
      {
        preset: 'conventionalcommits',
        presetConfig: {
          types: [
            { type: 'feat', section: 'Features' },
            { type: 'fix', section: 'Bug Fixes' },
            { type: 'perf', section: 'Performance' },
            { type: 'revert', section: 'Reverts' },
            { type: 'docs', section: 'Documentation', hidden: false },
            { type: 'style', section: 'Styles', hidden: true },
            { type: 'refactor', section: 'Refactoring', hidden: true },
            { type: 'test', section: 'Tests', hidden: true },
            { type: 'chore', section: 'Chores', hidden: true },
            { type: 'ci', section: 'CI', hidden: true },
            { type: 'build', section: 'Build', hidden: true }
          ]
        }
      }
    ],
    [
      '@semantic-release/exec',
      {
        prepareCmd:
          "python -c \"from pathlib import Path; import re; p = Path('pyproject.toml'); text = p.read_text(encoding='utf-8'); text = re.sub(r'^(version\\s*=\\s*)(\\\"[^\\\"]*\\\"|\\'[^\\']*\\')', r'\\1\\\"${nextRelease.version}\\\"', text, count=1, flags=re.MULTILINE); p.write_text(text, encoding='utf-8')\""
      }
    ],
    [
      '@semantic-release/changelog',
      {
        changelogFile: 'CHANGELOG.md',
        changelogTitle: '# Changelog\n\nAll notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/).\n'
      }
    ],
    [
      '@semantic-release/git',
      {
        assets: ['CHANGELOG.md', 'pyproject.toml'],
        message: 'chore(release): ${nextRelease.version} [skip ci]'
      }
    ],
    [
      '@semantic-release/github',
      {
        successComment: false,
        failComment: false,
        releasedLabels: false
      }
    ]
  ]
};
