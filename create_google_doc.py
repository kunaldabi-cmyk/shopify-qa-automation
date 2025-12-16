#!/usr/bin/env python3
"""
Google Docs Report Generator for GitHub Actions
Creates a formatted report with embedded screenshots
"""

import json
import os
from datetime import datetime
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class GoogleDocsQAReporter:
    def __init__(self, credentials_path):
        """Initialize Google API clients"""
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        
        self.docs = build('docs', 'v1', credentials=creds)
        self.drive = build('drive', 'v3', credentials=creds)
    
    def create_report(self, issues, store_url=''):
        """Create comprehensive QA report"""
        # Create document
        title = f'Shopify QA Report - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        doc = self.docs.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']
        
        print(f"✓ Created Google Doc: {doc_id}")
        
        # Build document content
        self._build_header(doc_id, issues, store_url)
        self._build_summary(doc_id, issues)
        self._add_issues_with_screenshots(doc_id, issues)
        
        # Share document
        self.drive.permissions().create(
            fileId=doc_id,
            body={'role': 'writer', 'type': 'anyone'}
        ).execute()
        
        doc_url = f'https://docs.google.com/document/d/{doc_id}/edit'
        
        # Save URL to file for GitHub Actions
        with open('google_doc_url.txt', 'w') as f:
            f.write(doc_url)
        
        print(f"✓ Report URL: {doc_url}")
        return doc_url
    
    def _build_header(self, doc_id, issues, store_url):
        """Build document header"""
        requests = []
        
        header_text = f'''Shopify QA Automation Report

Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
Store: {store_url}
Total Issues Found: {len(issues)}

'''
        
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': header_text
            }
        })
        
        # Style the title
        requests.append({
            'updateParagraphStyle': {
                'range': {'startIndex': 1, 'endIndex': 30},
                'paragraphStyle': {
                    'namedStyleType': 'HEADING_1',
                    'alignment': 'CENTER'
                },
                'fields': 'namedStyleType,alignment'
            }
        })
        
        self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
    
    def _build_summary(self, doc_id, issues):
        """Build executive summary"""
        # Get current end
        doc = self.docs.documents().get(documentId=doc_id).execute()
        end_idx = doc['body']['content'][-1]['endIndex'] - 1
        
        # Calculate statistics
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        category_counts = {}
        device_counts = {'desktop': 0, 'mobile': 0}
        
        for issue in issues:
            severity_counts[issue.get('severity', 'low')] += 1
            category = issue.get('category', 'Unknown')
            category_counts[category] = category_counts.get(category, 0) + 1
            device_counts[issue.get('device', 'desktop')] += 1
        
        # Build summary text
        summary = '''━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

'''
        
        # Severity breakdown
        summary += 'Issue Severity:\n'
        summary += f'  🔴 Critical: {severity_counts["critical"]}\n'
        summary += f'  🟠 High: {severity_counts["high"]}\n'
        summary += f'  🟡 Medium: {severity_counts["medium"]}\n'
        summary += f'  🟢 Low: {severity_counts["low"]}\n\n'
        
        # Device breakdown
        summary += 'Issues by Device:\n'
        summary += f'  💻 Desktop: {device_counts["desktop"]}\n'
        summary += f'  📱 Mobile: {device_counts["mobile"]}\n\n'
        
        # Top categories
        summary += 'Top Issue Categories:\n'
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary += f'  • {category}: {count}\n'
        
        summary += '\n'
        
        # Critical issues alert
        critical_issues = [i for i in issues if i.get('severity') in ['critical', 'high']]
        if critical_issues:
            summary += '⚠️  ATTENTION REQUIRED\n'
            summary += f'{len(critical_issues)} critical/high severity issues need immediate attention!\n\n'
        
        summary += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        
        self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{
                'insertText': {
                    'location': {'index': end_idx},
                    'text': summary
                }
            }]}
        ).execute()
    
    def _add_issues_with_screenshots(self, doc_id, issues):
        """Add all issues grouped by page with screenshots"""
        # Group issues by page URL
        issues_by_page = {}
        for issue in issues:
            url = issue.get('url', 'Unknown Page')
            if url not in issues_by_page:
                issues_by_page[url] = []
            issues_by_page[url].append(issue)
        
        # Add each page's issues
        for page_url, page_issues in issues_by_page.items():
            self._add_page_section(doc_id, page_url, page_issues)
    
    def _add_page_section(self, doc_id, page_url, issues):
        """Add issues for a specific page"""
        doc = self.docs.documents().get(documentId=doc_id).execute()
        end_idx = doc['body']['content'][-1]['endIndex'] - 1
        
        # Page header
        header = f'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nPAGE: {page_url}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        header += f'Issues found: {len(issues)}\n\n'
        
        self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{
                'insertText': {
                    'location': {'index': end_idx},
                    'text': header
                }
            }]}
        ).execute()
        
        # Add each issue
        for i, issue in enumerate(issues, 1):
            self._add_single_issue(doc_id, issue, i)
    
    def _add_single_issue(self, doc_id, issue, issue_num):
        """Add a single issue with screenshot"""
        doc = self.docs.documents().get(documentId=doc_id).execute()
        end_idx = doc['body']['content'][-1]['endIndex'] - 1
        
        # Severity emoji
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        emoji = severity_emoji.get(issue.get('severity', 'low'), '⚪')
        
        # Issue text
        issue_text = f'''
{emoji} Issue #{issue_num}: {issue.get('category', 'Unknown')}

Severity: {issue.get('severity', 'unknown').upper()}
Device: {issue.get('device', 'unknown').upper()}
Description: {issue.get('issue', 'No description')}
Time: {issue.get('timestamp', 'Unknown')}

'''
        
        # Insert text
        self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{
                'insertText': {
                    'location': {'index': end_idx},
                    'text': issue_text
                }
            }]}
        ).execute()
        
        # Insert screenshot if available
        screenshot_path = issue.get('screenshot')
        if screenshot_path and os.path.exists(screenshot_path):
            self._insert_screenshot(doc_id, screenshot_path)
        
        # Add separator
        doc = self.docs.documents().get(documentId=doc_id).execute()
        end_idx = doc['body']['content'][-1]['endIndex'] - 1
        
        self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{
                'insertText': {
                    'location': {'index': end_idx},
                    'text': '─' * 50 + '\n\n'
                }
            }]}
        ).execute()
    
    def _insert_screenshot(self, doc_id, screenshot_path):
        """Upload screenshot to Drive and insert into doc"""
        try:
            # Upload to Drive
            file_metadata = {
                'name': Path(screenshot_path).name,
                'mimeType': 'image/png'
            }
            
            media = MediaFileUpload(
                screenshot_path,
                mimetype='image/png',
                resumable=True
            )
            
            file = self.drive.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            image_id = file['id']
            
            # Make publicly accessible
            self.drive.permissions().create(
                fileId=image_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            # Get public URL
            image_url = f'https://drive.google.com/uc?id={image_id}'
            
            # Insert into document
            doc = self.docs.documents().get(documentId=doc_id).execute()
            end_idx = doc['body']['content'][-1]['endIndex'] - 1
            
            self.docs.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': [{
                    'insertInlineImage': {
                        'location': {'index': end_idx},
                        'uri': image_url,
                        'objectSize': {
                            'height': {'magnitude': 400, 'unit': 'PT'},
                            'width': {'magnitude': 600, 'unit': 'PT'}
                        }
                    }
                }]}
            ).execute()
            
            print(f"  ✓ Inserted screenshot: {Path(screenshot_path).name}")
            
        except Exception as e:
            print(f"  ✗ Failed to insert screenshot: {e}")


def main():
    """Main execution"""
    # Load credentials
    creds_path = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    
    if not os.path.exists(creds_path):
        print("Error: Google credentials not found!")
        print(f"Expected at: {creds_path}")
        exit(1)
    
    # Load QA report
    if not os.path.exists('qa-report.json'):
        print("Error: qa-report.json not found!")
        exit(1)
    
    with open('qa-report.json') as f:
        issues = json.load(f)
    
    print(f"\nCreating Google Doc for {len(issues)} issues...")
    
    # Create report
    reporter = GoogleDocsQAReporter(creds_path)
    
    # Get store URL from urls.txt if available
    store_url = ''
    if os.path.exists('urls.txt'):
        with open('urls.txt') as f:
            first_url = f.readline().strip()
            if first_url:
                from urllib.parse import urlparse
                parsed = urlparse(first_url)
                store_url = f"{parsed.scheme}://{parsed.netloc}"
    
    doc_url = reporter.create_report(issues, store_url)
    
    print(f"\n✓ Report created successfully!")
    print(f"✓ URL: {doc_url}")
    print(f"✓ URL saved to: google_doc_url.txt")


if __name__ == '__main__':
    main()
