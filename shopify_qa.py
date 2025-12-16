#!/usr/bin/env python3
"""
Enhanced Shopify QA Automation - Complete User Journey Testing
Tests complete purchase flow with screenshots at every step
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

class EnhancedShopifyQA:
    def __init__(self):
        self.screenshot_dir = Path('./qa-screenshots')
        self.screenshot_dir.mkdir(exist_ok=True)
        self.issues = []
        self.screenshot_counter = 0
    
    async def test_url(self, url, device='desktop'):
        """Test a single URL with complete user journey"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            if device == 'mobile':
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
                network_errors.append({'url': req.url, 'failure': str(req.failure)})
            )
            
            try:
                print(f"\n{'='*70}")
                print(f"Testing: {url}")
                print(f"Device: {device.upper()}")
                print('='*70)
                
                # STEP 1: Navigate to page
                print("\n[STEP 1] Loading page...")
                response = await page.goto(url, timeout=45000, wait_until='networkidle')
                
                # Wait 10-15 seconds as requested
                print("  Waiting 15 seconds for page to fully load...")
                await page.wait_for_timeout(15000)
                
                # Screenshot: Initial page load
                screenshot_path = await self.take_screenshot(
                    page, url, device, '01_page_loaded',
                    "Page loaded - initial view"
                )
                
                # Check HTTP status
                if response.status != 200:
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'high',
                        'category': 'HTTP Error',
                        'issue': f'Page returned status {response.status}',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Check for broken images
                broken_images = await page.evaluate('''
                    () => Array.from(document.querySelectorAll('img'))
                        .filter(img => !img.complete || img.naturalWidth === 0)
                        .length
                ''')
                
                if broken_images > 0:
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'high',
                        'category': 'Broken Images',
                        'issue': f'{broken_images} images failed to load',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # STEP 2: Look for "Front & Rear Seats" option
                print("\n[STEP 2] Looking for 'Front & Rear Seats' option...")
                
                # Try multiple selectors for the radio button
                seat_selectors = [
                    'input[type="radio"][value*="Front"][value*="Rear"]',
                    'input[value*="Front & Rear"]',
                    'input[value*="front-rear"]',
                    'label:has-text("Front & Rear Seats") input',
                    'input[id*="front-rear"]',
                    'input[name*="seat"][value*="both"]'
                ]
                
                seat_option = None
                for selector in seat_selectors:
                    try:
                        seat_option = await page.query_selector(selector)
                        if seat_option:
                            print(f"  ✓ Found seat option with selector: {selector}")
                            break
                    except:
                        continue
                
                # If radio input found, find its label for clicking
                if seat_option:
                    # Get the label associated with this input
                    label_element = await page.evaluate('''(input) => {
                        const id = input.id;
                        if (id) {
                            const label = document.querySelector(`label[for="${id}"]`);
                            if (label) return label;
                        }
                        // Or find parent label
                        return input.closest('label');
                    }''', seat_option)
                    
                    # Hover over the option
                    if label_element:
                        await page.hover(f'label[for="{await seat_option.get_attribute("id")}"]')
                    else:
                        await seat_option.hover()
                    
                    await page.wait_for_timeout(1000)
                    
                    # Screenshot: Before clicking seat option
                    screenshot_path = await self.take_screenshot(
                        page, url, device, '02_before_select_seats',
                        "Hovering over 'Front & Rear Seats' option"
                    )
                    
                    # Click the option
                    print("  Clicking 'Front & Rear Seats'...")
                    await seat_option.click(force=True)
                    await page.wait_for_timeout(2000)
                    
                    # Screenshot: After clicking seat option
                    screenshot_path = await self.take_screenshot(
                        page, url, device, '03_seats_selected',
                        "Selected 'Front & Rear Seats'"
                    )
                    print("  ✓ 'Front & Rear Seats' selected")
                
                else:
                    print("  ⚠ Could not find 'Front & Rear Seats' option")
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'high',
                        'category': 'Element Not Found',
                        'issue': 'Could not find "Front & Rear Seats" option',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # STEP 3: Wait for and click color selection button
                print("\n[STEP 3] Looking for color selection button...")
                await page.wait_for_timeout(2000)
                
                color_selectors = [
                    'button:has-text("Select Color")',
                    'button:has-text("Choose Color")',
                    'a:has-text("Select Color")',
                    'button[class*="color"]',
                    'button:has-text("Color")',
                    '.color-selector button',
                    'button:has-text("Select")'
                ]
                
                color_button = None
                for selector in color_selectors:
                    try:
                        color_button = await page.query_selector(selector)
                        if color_button and await color_button.is_visible():
                            print(f"  ✓ Found color button with selector: {selector}")
                            break
                    except:
                        continue
                
                if color_button:
                    # Hover over color button
                    await color_button.hover()
                    await page.wait_for_timeout(1000)
                    
                    # Screenshot: Before clicking color button
                    screenshot_path = await self.take_screenshot(
                        page, url, device, '04_before_color_select',
                        "Hovering over color selection button"
                    )
                    
                    # Click color button
                    print("  Clicking color selection button...")
                    await color_button.click()
                    await page.wait_for_timeout(2000)
                    
                    # Screenshot: After clicking color button
                    screenshot_path = await self.take_screenshot(
                        page, url, device, '05_color_options_visible',
                        "Color options displayed"
                    )
                    print("  ✓ Color selection opened")
                
                else:
                    print("  ⚠ Color selection button not found")
                
                # STEP 4: Select black color (or any available)
                print("\n[STEP 4] Selecting color...")
                
                color_option_selectors = [
                    'button:has-text("Black")',
                    'label:has-text("Black")',
                    'input[value*="black"]',
                    'div[data-color="black"]',
                    'button[title*="Black"]',
                    # Fallback to any color
                    'button[class*="color-option"]:first-child',
                    '.color-swatch:first-child'
                ]
                
                color_selected = False
                for selector in color_option_selectors:
                    try:
                        color_option = await page.query_selector(selector)
                        if color_option and await color_option.is_visible():
                            # Hover
                            await color_option.hover()
                            await page.wait_for_timeout(1000)
                            
                            # Screenshot: Before selecting color
                            screenshot_path = await self.take_screenshot(
                                page, url, device, '06_before_color_click',
                                f"Hovering over color option"
                            )
                            
                            # Click
                            print(f"  Clicking color option...")
                            await color_option.click()
                            await page.wait_for_timeout(2000)
                            
                            # Screenshot: After selecting color
                            screenshot_path = await self.take_screenshot(
                                page, url, device, '07_color_selected',
                                "Color selected"
                            )
                            
                            print("  ✓ Color selected")
                            color_selected = True
                            break
                    except:
                        continue
                
                if not color_selected:
                    print("  ⚠ Could not select color")
                
                # STEP 5: Click "Add to Cart"
                print("\n[STEP 5] Looking for 'Add to Cart' button...")
                
                add_to_cart_selectors = [
                    'button:has-text("Add to Cart")',
                    'button[name="add"]',
                    'button[type="submit"]:has-text("Add")',
                    'input[type="submit"][value*="Add"]',
                    'button.add-to-cart',
                    'button[class*="add-cart"]',
                    '.product-form__submit'
                ]
                
                cart_added = False
                for selector in add_to_cart_selectors:
                    try:
                        add_button = await page.query_selector(selector)
                        if add_button and await add_button.is_visible() and await add_button.is_enabled():
                            # Hover
                            await add_button.hover()
                            await page.wait_for_timeout(1000)
                            
                            # Screenshot: Before adding to cart
                            screenshot_path = await self.take_screenshot(
                                page, url, device, '08_before_add_to_cart',
                                "Hovering over 'Add to Cart' button"
                            )
                            
                            # Click
                            print("  Clicking 'Add to Cart'...")
                            await add_button.click()
                            await page.wait_for_timeout(3000)  # Wait for cart popup
                            
                            # Screenshot: After adding to cart (with popup)
                            screenshot_path = await self.take_screenshot(
                                page, url, device, '09_added_to_cart_popup',
                                "Item added to cart - popup visible"
                            )
                            
                            print("  ✓ Added to cart")
                            cart_added = True
                            break
                    except Exception as e:
                        print(f"  Error with selector {selector}: {str(e)}")
                        continue
                
                if not cart_added:
                    print("  ✗ Failed to add to cart")
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'critical',
                        'category': 'Add to Cart Failed',
                        'issue': 'Could not add product to cart',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # STEP 6: Find and click "Continue to Checkout" in popup
                print("\n[STEP 6] Looking for 'Continue to Checkout' button...")
                await page.wait_for_timeout(2000)
                
                checkout_selectors = [
                    'button:has-text("Continue to Checkout")',
                    'a:has-text("Continue to Checkout")',
                    'button:has-text("Checkout")',
                    'a:has-text("Checkout")',
                    'a[href*="checkout"]',
                    'button[class*="checkout"]',
                    '.cart-popup button:has-text("Checkout")',
                    'button.btn-checkout'
                ]
                
                checkout_clicked = False
                for selector in checkout_selectors:
                    try:
                        checkout_button = await page.query_selector(selector)
                        if checkout_button and await checkout_button.is_visible():
                            # Scroll into view
                            await checkout_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(1000)
                            
                            # Hover
                            await checkout_button.hover()
                            await page.wait_for_timeout(1000)
                            
                            # Screenshot: Before clicking checkout
                            screenshot_path = await self.take_screenshot(
                                page, url, device, '10_before_checkout_click',
                                "Hovering over 'Continue to Checkout' button"
                            )
                            
                            # Click
                            print("  Clicking 'Continue to Checkout'...")
                            await checkout_button.click()
                            
                            # Wait for navigation
                            await page.wait_for_load_state('networkidle', timeout=15000)
                            
                            # Additional wait for checkout page
                            print("  Waiting 10 seconds for checkout page to load...")
                            await page.wait_for_timeout(10000)
                            
                            # Screenshot: Checkout page loaded
                            screenshot_path = await self.take_screenshot(
                                page, url, device, '11_checkout_page_loaded',
                                "Checkout page fully loaded"
                            )
                            
                            # Verify we're on checkout
                            current_url = page.url
                            if 'checkout' in current_url.lower():
                                print(f"  ✓ Successfully reached checkout page")
                                print(f"  Checkout URL: {current_url}")
                            else:
                                print(f"  ⚠ May not be on checkout page")
                                print(f"  Current URL: {current_url}")
                                await self.log_issue({
                                    'url': url,
                                    'device': device,
                                    'severity': 'high',
                                    'category': 'Checkout Navigation',
                                    'issue': f'Clicked checkout but URL is: {current_url}',
                                    'screenshot': screenshot_path,
                                    'timestamp': datetime.now().isoformat()
                                })
                            
                            checkout_clicked = True
                            break
                    except Exception as e:
                        print(f"  Error with selector {selector}: {str(e)}")
                        continue
                
                if not checkout_clicked:
                    print("  ✗ Failed to click checkout button")
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'critical',
                        'category': 'Checkout Button Not Found',
                        'issue': 'Could not find or click checkout button',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Final screenshot
                screenshot_path = await self.take_screenshot(
                    page, url, device, '12_final_state',
                    "Final page state"
                )
                
                # Log any console errors
                if console_errors:
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'medium',
                        'category': 'JavaScript Errors',
                        'issue': f'Console errors: {len(console_errors)} errors detected',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Log network errors
                if network_errors:
                    await self.log_issue({
                        'url': url,
                        'device': device,
                        'severity': 'medium',
                        'category': 'Network Errors',
                        'issue': f'Failed to load {len(network_errors)} resources',
                        'screenshot': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    })
                
                print("\n" + "="*70)
                print(f"✓ Completed testing {url} on {device}")
                print("="*70)
            
            except Exception as e:
                print(f"\n✗ ERROR: {str(e)}")
                screenshot_path = await self.take_screenshot(
                    page, url, device, 'error',
                    f"Error occurred: {str(e)}"
                )
                
                await self.log_issue({
                    'url': url,
                    'device': device,
                    'severity': 'critical',
                    'category': 'Test Failure',
                    'issue': f'Test failed: {str(e)}',
                    'screenshot': screenshot_path,
                    'timestamp': datetime.now().isoformat()
                })
            
            await browser.close()
    
    async def take_screenshot(self, page, url, device, step_name, description):
        """Take a screenshot with metadata"""
        try:
            self.screenshot_counter += 1
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Clean URL for filename
            url_part = url.split('/')[-1][:30] if '/' in url else 'page'
            
            filename = f"{self.screenshot_counter:03d}_{device}_{step_name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            
            await page.screenshot(path=filepath, full_page=True)
            
            print(f"  📸 Screenshot: {filename}")
            print(f"     {description}")
            
            return str(filepath)
        except Exception as e:
            print(f"  ✗ Screenshot failed: {str(e)}")
            return None
    
    async def log_issue(self, issue):
        """Log an issue"""
        self.issues.append(issue)
        
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        emoji = severity_emoji.get(issue['severity'], '⚪')
        
        print(f"\n  {emoji} ISSUE LOGGED:")
        print(f"     Severity: {issue['severity'].upper()}")
        print(f"     Category: {issue['category']}")
        print(f"     Details: {issue['issue']}")
    
    async def run_tests(self, urls):
        """Run tests on all URLs"""
        print("\n" + "="*70)
        print("ENHANCED SHOPIFY QA AUTOMATION")
        print("Complete User Journey Testing")
        print("="*70)
        print(f"\nTesting {len(urls)} URL(s)")
        print(f"Each URL tested on: Desktop + Mobile")
        print(f"Screenshots will be saved to: {self.screenshot_dir}")
        print("\n" + "="*70)
        
        for url in urls:
            # Test on desktop
            await self.test_url(url, 'desktop')
            
            # Short break between tests
            await asyncio.sleep(2)
            
            # Test on mobile
            await self.test_url(url, 'mobile')
            
            # Break between URLs
            await asyncio.sleep(2)
        
        # Save report
        with open('qa-report.json', 'w') as f:
            json.dump(self.issues, f, indent=2)
        
        # Print summary
        print("\n" + "="*70)
        print("TESTING COMPLETE!")
        print("="*70)
        print(f"\nTotal Screenshots: {self.screenshot_counter}")
        print(f"Total Issues Found: {len(self.issues)}")
        
        # Issue breakdown
        severity_count = {}
        for issue in self.issues:
            sev = issue['severity']
            severity_count[sev] = severity_count.get(sev, 0) + 1
        
        if severity_count:
            print("\nIssues by Severity:")
            for sev in ['critical', 'high', 'medium', 'low']:
                if sev in severity_count:
                    emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[sev]
                    print(f"  {emoji} {sev.title()}: {severity_count[sev]}")
        
        print(f"\nReport saved to: qa-report.json")
        print(f"Screenshots saved to: {self.screenshot_dir}/")
        print("="*70 + "\n")
        
        return self.issues


async def main():
    """Main execution"""
    urls = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not urls:
        if os.path.exists('urls.txt'):
            with open('urls.txt') as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    if not urls:
        print("Error: No URLs provided")
        print("\nUsage:")
        print("  python shopify_qa.py <url1> [url2] ...")
        print("  or create urls.txt file with one URL per line")
        sys.exit(1)
    
    qa = EnhancedShopifyQA()
    await qa.run_tests(urls)


if __name__ == '__main__':
    asyncio.run(main())
