#!/usr/bin/env python3
"""
Simplified Shopify QA Automation (Python)
Easier setup than Node.js version - good for quick testing
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import base64

class ShopifyQA:
    def __init__(self, screenshot_dir='./qa-screenshots'):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True)
        self.issues = []
        self.screenshot_counter = 0
        
    async def run_tests(self, urls):
        """Run QA tests on list of URLs"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for url in urls:
                print(f"\n=== Testing: {url} ===")
                
                # Test Desktop
                await self.test_page(browser, url, 'desktop')
                
                # Test Mobile
                await self.test_page(browser, url, 'mobile')
            
            await browser.close()
        
        return self.issues
    
    async def test_page(self, browser, url, device_type):
        """Test a single page on specific device"""
        if device_type == 'mobile':
            context = await browser.new_context(
                viewport={'width': 375, 'height': 812},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                is_mobile=True,
                has_touch=True
            )
        else:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
        
        page = await context.new_page()
        
        # Track errors
        console_errors = []
        network_errors = []
        
        page.on('console', lambda msg: 
            console_errors.append(msg.text) if msg.type == 'error' else None
        )
        
        page.on('requestfailed', lambda req:
            network_errors.append({
                'url': req.url,
                'failure': req.failure
            })
        )
        
        try:
            # Navigate
            print(f"Loading {url} ({device_type})...")
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Initial screenshot
            initial_screenshot = await self.take_screenshot(page, url, device_type, 'initial')
            
            # Check HTTP status
            if response.status != 200:
                await self.log_issue({
                    'page': url,
                    'device': device_type,
                    'severity': 'high',
                    'category': 'HTTP Error',
                    'issue': f'Page returned status code {response.status}',
                    'screenshot': initial_screenshot
                })
            
            # Check visual issues
            await self.check_visual_issues(page, url, device_type)
            
            # Check console errors
            if console_errors:
                await self.log_issue({
                    'page': url,
                    'device': device_type,
                    'severity': 'medium',
                    'category': 'JavaScript Error',
                    'issue': f'Console errors: {", ".join(console_errors[:3])}',
                    'screenshot': initial_screenshot
                })
            
            # Check network failures
            if network_errors:
                screenshot = await self.take_screenshot(page, url, device_type, 'network-error')
                await self.log_issue({
                    'page': url,
                    'device': device_type,
                    'severity': 'high',
                    'category': 'Network Error',
                    'issue': f'Failed resources: {", ".join([e["url"] for e in network_errors[:3]])}',
                    'screenshot': screenshot
                })
            
            # Check if product page
            is_product = await page.evaluate('''() => {
                return document.querySelector('[data-product-json]') !== null ||
                       document.querySelector('.product-form') !== null ||
                       document.querySelector('form[action*="/cart/add"]') !== null;
            }''')
            
            if is_product:
                await self.test_product_page(page, url, device_type)
        
        except Exception as e:
            screenshot = await self.take_screenshot(page, url, device_type, 'error')
            await self.log_issue({
                'page': url,
                'device': device_type,
                'severity': 'critical',
                'category': 'Page Load Error',
                'issue': f'Failed to test page: {str(e)}',
                'screenshot': screenshot
            })
        
        await context.close()
    
    async def check_visual_issues(self, page, url, device_type):
        """Check for visual/layout issues"""
        
        # Check broken images
        broken_images = await page.evaluate('''() => {
            const images = Array.from(document.querySelectorAll('img'));
            return images
                .filter(img => !img.complete || img.naturalWidth === 0)
                .map(img => ({ src: img.src, alt: img.alt || 'No alt' }));
        }''')
        
        if broken_images:
            screenshot = await self.take_screenshot(page, url, device_type, 'broken-images')
            await self.log_issue({
                'page': url,
                'device': device_type,
                'severity': 'high',
                'category': 'Broken Images',
                'issue': f'{len(broken_images)} images failed to load',
                'screenshot': screenshot
            })
        
        # Check for overlapping elements (simplified)
        overlaps = await page.evaluate('''() => {
            function overlap(el1, el2) {
                const r1 = el1.getBoundingClientRect();
                const r2 = el2.getBoundingClientRect();
                return !(r1.right < r2.left || r1.left > r2.right || 
                         r1.bottom < r2.top || r1.top > r2.bottom);
            }
            
            const elements = Array.from(document.querySelectorAll('button, a, input'));
            let count = 0;
            
            for (let i = 0; i < elements.length && count < 5; i++) {
                for (let j = i + 1; j < elements.length; j++) {
                    if (overlap(elements[i], elements[j])) count++;
                }
            }
            
            return count;
        }''')
        
        if overlaps > 0:
            screenshot = await self.take_screenshot(page, url, device_type, 'overlapping')
            await self.log_issue({
                'page': url,
                'device': device_type,
                'severity': 'medium',
                'category': 'Layout Issue',
                'issue': f'{overlaps} overlapping elements detected',
                'screenshot': screenshot
            })
    
    async def test_product_page(self, page, url, device_type):
        """Test product page functionality"""
        print(f"Testing product page ({device_type})...")
        
        try:
            # Check stock status
            sold_out = await page.evaluate('''() => {
                const text = document.body.innerText.toLowerCase();
                return text.includes('sold out') || text.includes('unavailable') ||
                       document.querySelector('[disabled]') !== null;
            }''')
            
            if sold_out:
                screenshot = await self.take_screenshot(page, url, device_type, 'out-of-stock')
                await self.log_issue({
                    'page': url,
                    'device': device_type,
                    'severity': 'high',
                    'category': 'Stock Status',
                    'issue': 'Product out of stock',
                    'screenshot': screenshot
                })
                return
            
            # Try to add to cart
            selectors = [
                'button[name="add"]',
                'button[type="submit"].product-form__submit',
                'button:has-text("Add to cart")',
                '.product-form__submit'
            ]
            
            added = False
            for selector in selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible() and await button.is_enabled():
                        before_screenshot = await self.take_screenshot(
                            page, url, device_type, 'before-add-cart'
                        )
                        
                        await button.click()
                        await page.wait_for_timeout(2000)
                        
                        after_screenshot = await self.take_screenshot(
                            page, url, device_type, 'after-add-cart'
                        )
                        
                        added = True
                        print('✓ Added to cart')
                        break
                except:
                    continue
            
            if not added:
                screenshot = await self.take_screenshot(page, url, device_type, 'cart-failed')
                await self.log_issue({
                    'page': url,
                    'device': device_type,
                    'severity': 'critical',
                    'category': 'Cart Functionality',
                    'issue': 'Could not add to cart',
                    'screenshot': screenshot
                })
                return
            
            # Navigate to cart
            await self.test_cart_checkout(page, url, device_type)
        
        except Exception as e:
            screenshot = await self.take_screenshot(page, url, device_type, 'product-error')
            await self.log_issue({
                'page': url,
                'device': device_type,
                'severity': 'high',
                'category': 'Product Page Error',
                'issue': f'Error: {str(e)}',
                'screenshot': screenshot
            })
    
    async def test_cart_checkout(self, page, url, device_type):
        """Test cart and checkout flow"""
        try:
            # Try cart links
            cart_selectors = ['a[href="/cart"]', 'a[href*="/cart"]', '.cart-link']
            
            navigated = False
            for selector in cart_selectors:
                try:
                    link = await page.query_selector(selector)
                    if link and await link.is_visible():
                        await link.click()
                        await page.wait_for_load_state('networkidle')
                        
                        cart_screenshot = await self.take_screenshot(
                            page, url, device_type, 'cart-page'
                        )
                        
                        navigated = True
                        print('✓ Navigated to cart')
                        break
                except:
                    continue
            
            if not navigated:
                # Try direct navigation
                cart_url = page.url.split('/')[0:3]
                cart_url = '/'.join(cart_url) + '/cart'
                await page.goto(cart_url)
                await page.wait_for_load_state('networkidle')
            
            # Try checkout
            checkout_selectors = [
                'button[name="checkout"]',
                'input[value*="Checkout"]',
                'button:has-text("Checkout")',
                '.cart__checkout-button'
            ]
            
            for selector in checkout_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        before_checkout = await self.take_screenshot(
                            page, url, device_type, 'before-checkout'
                        )
                        
                        await button.click()
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        
                        after_checkout = await self.take_screenshot(
                            page, url, device_type, 'checkout-page'
                        )
                        
                        # Check if on checkout
                        on_checkout = await page.evaluate('''() => {
                            return window.location.hostname.includes('checkout') ||
                                   window.location.pathname.includes('checkout') ||
                                   document.body.innerText.includes('Shipping address');
                        }''')
                        
                        if on_checkout:
                            print('✓ Reached checkout')
                        else:
                            await self.log_issue({
                                'page': url,
                                'device': device_type,
                                'severity': 'high',
                                'category': 'Checkout Navigation',
                                'issue': 'Checkout button clicked but not on checkout page',
                                'screenshot': after_checkout
                            })
                        break
                except:
                    continue
        
        except Exception as e:
            screenshot = await self.take_screenshot(page, url, device_type, 'checkout-error')
            await self.log_issue({
                'page': url,
                'device': device_type,
                'severity': 'high',
                'category': 'Checkout Flow',
                'issue': f'Checkout error: {str(e)}',
                'screenshot': screenshot
            })
    
    async def take_screenshot(self, page, url, device_type, label):
        """Take and save screenshot"""
        try:
            self.screenshot_counter += 1
            filename = f'{self.screenshot_counter}_{device_type}_{label}_{int(datetime.now().timestamp())}.png'
            filepath = self.screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            return str(filepath)
        except Exception as e:
            print(f'Screenshot failed: {e}')
            return None
    
    async def log_issue(self, issue):
        """Log an issue"""
        self.issues.append({
            'timestamp': datetime.now().isoformat(),
            **issue
        })
        
        severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
        emoji = severity_emoji.get(issue['severity'], '⚪')
        print(f"{emoji} {issue['severity'].upper()}: {issue['category']} - {issue['issue']}")


class GoogleDocsReporter:
    """Generate Google Docs report with screenshots"""
    
    def __init__(self, credentials_path):
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        
        self.docs_service = build('docs', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
    
    def create_report(self, issues, store_url=''):
        """Create QA report in Google Docs"""
        title = f'Shopify QA Report - {datetime.now().strftime("%Y-%m-%d")}'
        
        # Create document
        doc = self.docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']
        
        print(f'Created document: {doc_id}')
        
        # Build content
        self._build_content(doc_id, issues, store_url)
        
        # Share document
        self.drive_service.permissions().create(
            fileId=doc_id,
            body={'role': 'writer', 'type': 'anyone'}
        ).execute()
        
        doc_url = f'https://docs.google.com/document/d/{doc_id}/edit'
        print(f'Report: {doc_url}')
        
        return {'documentId': doc_id, 'url': doc_url}
    
    def _build_content(self, doc_id, issues, store_url):
        """Build document content"""
        requests = []
        
        # Title
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': f'Shopify QA Report\n\n'
            }
        })
        
        # Metadata
        metadata = f'''Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Store: {store_url}
Total Issues: {len(issues)}

'''
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': metadata
            }
        })
        
        # Summary
        summary = self._generate_summary(issues)
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': f'Summary\n{summary}\n\n'
            }
        })
        
        # Execute
        if requests:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
        
        # Add issues
        self._add_issues(doc_id, issues)
    
    def _generate_summary(self, issues):
        """Generate summary text"""
        from collections import Counter
        
        severity_counts = Counter(i['severity'] for i in issues)
        category_counts = Counter(i['category'] for i in issues)
        
        summary = 'Severity Breakdown:\n'
        for severity, count in severity_counts.most_common():
            summary += f'  • {severity.title()}: {count}\n'
        
        summary += '\nTop Categories:\n'
        for category, count in list(category_counts.most_common(5)):
            summary += f'  • {category}: {count}\n'
        
        critical = [i for i in issues if i['severity'] in ['critical', 'high']]
        if critical:
            summary += '\n⚠️ Critical Issues:\n'
            for issue in critical[:5]:
                summary += f'  • {issue["page"]} ({issue["device"]}): {issue["issue"]}\n'
        
        return summary
    
    def _add_issues(self, doc_id, issues):
        """Add issues section"""
        # Group by page
        from collections import defaultdict
        by_page = defaultdict(list)
        for issue in issues:
            by_page[issue['page']].append(issue)
        
        # Add each page's issues
        for page_url, page_issues in by_page.items():
            self._add_page_issues(doc_id, page_url, page_issues)
    
    def _add_page_issues(self, doc_id, page_url, issues):
        """Add issues for a specific page"""
        # Get current length
        doc = self.docs_service.documents().get(documentId=doc_id).execute()
        end_index = doc['body']['content'][-1]['endIndex'] - 1
        
        # Add page heading
        text = f'\n\nPage: {page_url}\n'
        
        for issue in issues:
            severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
            emoji = severity_emoji.get(issue['severity'], '⚪')
            
            text += f'\n{emoji} {issue["severity"].upper()} - {issue["category"]} ({issue["device"]})\n'
            text += f'{issue["issue"]}\n'
            text += f'Time: {issue["timestamp"]}\n\n'
        
        self.docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={
                'requests': [{
                    'insertText': {
                        'location': {'index': end_index},
                        'text': text
                    }
                }]
            }
        ).execute()


# Main execution
async def main():
    import sys
    
    if len(sys.argv) < 2:
        print('Usage: python shopify_qa.py <url1> [url2] ...')
        sys.exit(1)
    
    urls = sys.argv[1:]
    
    # Run QA tests
    qa = ShopifyQA()
    issues = await qa.run_tests(urls)
    
    print(f'\n=== QA Complete ===')
    print(f'Total issues: {len(issues)}')
    
    # Save to JSON
    with open('qa-report.json', 'w') as f:
        json.dump(issues, f, indent=2)
    print('Saved to qa-report.json')
    
    # Generate Google Doc (if credentials available)
    creds_path = os.environ.get('GOOGLE_CREDENTIALS_PATH')
    if creds_path and os.path.exists(creds_path):
        reporter = GoogleDocsReporter(creds_path)
        result = reporter.create_report(issues, urls[0] if urls else '')
        print(f'Report URL: {result["url"]}')
    else:
        print('Tip: Set GOOGLE_CREDENTIALS_PATH to auto-generate Google Doc report')


if __name__ == '__main__':
    asyncio.run(main())
