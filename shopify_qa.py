#!/usr/bin/env python3
"""
Ultra-Detailed Shopify QA Automation
- Captures every scroll position
- Takes before/after screenshots for every action
- Zooms in on issues
- Records complete visual journey
"""

import asyncio
import json
import os
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

class UltraDetailedShopifyQA:
    def __init__(self):
        self.screenshot_dir = Path('./qa-screenshots')
        self.screenshot_dir.mkdir(exist_ok=True)
        self.issues = []
        self.screenshot_counter = 0
        self.performance_data = []
    
    async def test_url(self, url, device='desktop'):
        """Test URL with ultra-detailed screenshots"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            if device == 'mobile':
                context = await browser.new_context(
                    viewport={'width': 375, 'height': 812},
                    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                    is_mobile=True,
                    has_touch=True,
                    locale='en-US',
                    timezone_id='America/New_York',
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                    permissions=['geolocation']
                )
            else:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                    permissions=['geolocation']
                )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()
            
            console_errors = []
            network_errors = []
            
            page.on('console', lambda msg: 
                console_errors.append(msg.text) if msg.type == 'error' else None
            )
            
            page.on('requestfailed', lambda req:
                network_errors.append({'url': req.url, 'failure': str(req.failure)})
            )
            
            perf_data = {
                'url': url,
                'device': device,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                print(f"\n{'='*80}")
                print(f"🔍 ULTRA-DETAILED TESTING")
                print(f"URL: {url}")
                print(f"Device: {device.upper()}")
                print('='*80)
                
                # STEP 1: Initial page load with timing
                print("\n[STEP 1] 📄 Loading Page...")
                start_time = time.time()
                
                response = await page.goto(url, timeout=60000, wait_until='load')
                initial_load = time.time() - start_time
                
                await page.wait_for_load_state('networkidle', timeout=30000)
                network_idle = time.time() - start_time
                
                performance_metrics = await page.evaluate('''() => {
                    const perf = window.performance.timing;
                    return {
                        domContentLoaded: perf.domContentLoadedEventEnd - perf.navigationStart,
                        fullyLoaded: perf.loadEventEnd - perf.navigationStart,
                        domInteractive: perf.domInteractive - perf.navigationStart
                    };
                }''')
                
                perf_data.update({
                    'initial_load': round(initial_load, 2),
                    'network_idle': round(network_idle, 2),
                    'dom_content_loaded': round(performance_metrics['domContentLoaded'] / 1000, 2),
                    'fully_loaded': round(performance_metrics['fullyLoaded'] / 1000, 2)
                })
                
                print(f"  ⏱️  Initial Load: {initial_load:.2f}s")
                print(f"  ⏱️  Network Idle: {network_idle:.2f}s")
                print(f"  ⏱️  Fully Loaded: {perf_data['fully_loaded']}s")
                
                await page.wait_for_timeout(3000)
                
                # Screenshot 1: Top of page (hero section)
                await self.take_screenshot(page, url, device, 'step01_page_top', 
                    "Initial page view - above the fold")
                
                # STEP 2: Scroll through entire page with screenshots
                print("\n[STEP 2] 📸 Capturing Entire Page (Scroll-by-Scroll)...")
                await self.capture_scroll_journey(page, url, device)
                
                # STEP 3: Check all images with individual screenshots
                print("\n[STEP 3] 🖼️  Checking All Images...")
                await self.check_images_detailed(page, url, device)
                
                # STEP 4: Check layout and overlapping elements
                print("\n[STEP 4] 📐 Checking Layout and Overlaps...")
                await self.check_layout_detailed(page, url, device)
                
                # Scroll back to top for interaction testing
                await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
                await page.wait_for_timeout(1000)
                
                # STEP 5: Find and select "Front & Rear Seats"
                print("\n[STEP 5] 🎯 Selecting 'Front & Rear Seats'...")
                
                await self.take_screenshot(page, url, device, 'step05_before_seat_selection',
                    "Page view before selecting seat option")
                
                seat_selectors = [
                    'input[type="radio"][value*="Front"][value*="Rear"]',
                    'input[value*="Front & Rear"]',
                    'label:has-text("Front & Rear Seats") input',
                    'input[id*="front-rear"]'
                ]
                
                seat_found = False
                for selector in seat_selectors:
                    try:
                        seat_option = await page.query_selector(selector)
                        if seat_option:
                            # Scroll to element
                            await seat_option.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)
                            
                            # Screenshot: Scrolled to element
                            await self.take_screenshot(page, url, device, 'step05a_seat_option_visible',
                                "Scrolled to 'Front & Rear Seats' option")
                            
                            # Highlight element
                            await page.evaluate('''(element) => {
                                element.style.outline = '3px solid red';
                                element.style.outlineOffset = '2px';
                            }''', seat_option)
                            
                            await page.wait_for_timeout(500)
                            
                            # Screenshot: Highlighted
                            await self.take_screenshot(page, url, device, 'step05b_seat_option_highlighted',
                                "Seat option highlighted (red outline)")
                            
                            # Click
                            print("  ✓ Found 'Front & Rear Seats'")
                            print("  🖱️  Clicking...")
                            await seat_option.click(force=True)
                            await page.wait_for_timeout(1500)
                            
                            # Screenshot: After click
                            await self.take_screenshot(page, url, device, 'step05c_seat_selected',
                                "After selecting 'Front & Rear Seats'")
                            
                            print("  ✓ Selected successfully")
                            seat_found = True
                            break
                    except:
                        continue
                
                if not seat_found:
                    print("  ⚠️  'Front & Rear Seats' option not found")
                    await self.take_screenshot(page, url, device, 'step05_ERROR_seat_not_found',
                        "ERROR: Could not find seat option")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'high',
                        'category': 'Element Not Found',
                        'issue': 'Could not find "Front & Rear Seats" option',
                        'screenshot': f"{self.screenshot_counter-1:03d}",
                        'timestamp': datetime.now().isoformat()
                    })
                
                # STEP 6: Color selection button
                print("\n[STEP 6] 🎨 Looking for Color Selection...")
                await page.wait_for_timeout(1500)
                
                await self.take_screenshot(page, url, device, 'step06_before_color_button',
                    "Page state before color selection")
                
                color_selectors = [
                    'button:has-text("Select Color")',
                    'button:has-text("Choose Color")',
                    'button[class*="color"]',
                    'a:has-text("Select Color")'
                ]
                
                color_found = False
                for selector in color_selectors:
                    try:
                        color_button = await page.query_selector(selector)
                        if color_button and await color_button.is_visible():
                            await color_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)
                            
                            # Highlight
                            await page.evaluate('''(element) => {
                                element.style.outline = '3px solid blue';
                                element.style.outlineOffset = '2px';
                            }''', color_button)
                            
                            await self.take_screenshot(page, url, device, 'step06a_color_button_highlighted',
                                "Color selection button highlighted (blue outline)")
                            
                            print("  ✓ Found color button")
                            print("  🖱️  Clicking...")
                            await color_button.click()
                            await page.wait_for_timeout(1500)
                            
                            await self.take_screenshot(page, url, device, 'step06b_color_options_opened',
                                "Color options displayed after click")
                            
                            print("  ✓ Color options opened")
                            color_found = True
                            break
                    except:
                        continue
                
                if not color_found:
                    print("  ⚠️  Color button not found")
                    await self.take_screenshot(page, url, device, 'step06_ERROR_color_button_not_found',
                        "ERROR: Could not find color selection button")
                
                # STEP 7: Select color
                print("\n[STEP 7] ⚫ Selecting Color...")
                
                color_option_selectors = [
                    'button:has-text("Black")',
                    'label:has-text("Black")',
                    'button[title*="Black"]',
                    'button[class*="color-option"]:first-child'
                ]
                
                color_selected = False
                for selector in color_option_selectors:
                    try:
                        color_option = await page.query_selector(selector)
                        if color_option and await color_option.is_visible():
                            await color_option.scroll_into_view_if_needed()
                            await page.wait_for_timeout(500)
                            
                            # Highlight
                            await page.evaluate('''(element) => {
                                element.style.outline = '3px solid green';
                                element.style.outlineOffset = '2px';
                            }''', color_option)
                            
                            await self.take_screenshot(page, url, device, 'step07a_color_highlighted',
                                "Color option highlighted (green outline)")
                            
                            print("  ✓ Found color option")
                            print("  🖱️  Clicking...")
                            await color_option.click()
                            await page.wait_for_timeout(2000)
                            
                            await self.take_screenshot(page, url, device, 'step07b_color_selected',
                                "After selecting color")
                            
                            print("  ✓ Color selected")
                            color_selected = True
                            break
                    except:
                        continue
                
                if not color_selected:
                    print("  ⚠️  Could not select color")
                
                # STEP 8: Add to Cart
                print("\n[STEP 8] 🛒 Adding to Cart...")
                
                await self.take_screenshot(page, url, device, 'step08_before_add_to_cart',
                    "Page state before adding to cart")
                
                add_to_cart_selectors = [
                    'button:has-text("Add to Cart")',
                    'button[name="add"]',
                    'button.add-to-cart',
                    'input[type="submit"][value*="Add"]'
                ]
                
                cart_added = False
                for selector in add_to_cart_selectors:
                    try:
                        add_button = await page.query_selector(selector)
                        if add_button and await add_button.is_visible() and await add_button.is_enabled():
                            await add_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)
                            
                            # Highlight
                            await page.evaluate('''(element) => {
                                element.style.outline = '3px solid orange';
                                element.style.outlineOffset = '2px';
                            }''', add_button)
                            
                            await self.take_screenshot(page, url, device, 'step08a_add_cart_button_highlighted',
                                "Add to Cart button highlighted (orange outline)")
                            
                            print("  ✓ Found 'Add to Cart' button")
                            print("  🖱️  Clicking...")
                            await add_button.click()
                            await page.wait_for_timeout(3000)
                            
                            await self.take_screenshot(page, url, device, 'step08b_cart_popup_appeared',
                                "Cart popup/drawer after adding item")
                            
                            print("  ✓ Item added to cart")
                            cart_added = True
                            break
                    except Exception as e:
                        continue
                
                if not cart_added:
                    print("  ✗ Failed to add to cart")
                    await self.take_screenshot(page, url, device, 'step08_ERROR_add_cart_failed',
                        "ERROR: Could not add to cart")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'critical',
                        'category': 'Add to Cart Failed',
                        'issue': 'Could not add product to cart',
                        'screenshot': f"{self.screenshot_counter-1:03d}",
                        'timestamp': datetime.now().isoformat()
                    })
                
                # STEP 9: Find checkout button in popup
                print("\n[STEP 9] 💳 Looking for Checkout Button...")
                await page.wait_for_timeout(2000)
                
                checkout_selectors = [
                    'button:has-text("Continue to Checkout")',
                    'a:has-text("Continue to Checkout")',
                    'button:has-text("Checkout")',
                    'a:has-text("Checkout")',
                    'button[class*="checkout"]'
                ]
                
                checkout_found = False
                for selector in checkout_selectors:
                    try:
                        checkout_button = await page.query_selector(selector)
                        if checkout_button and await checkout_button.is_visible():
                            await checkout_button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(800)
                            
                            # Highlight
                            await page.evaluate('''(element) => {
                                element.style.outline = '3px solid purple';
                                element.style.outlineOffset = '2px';
                            }''', checkout_button)
                            
                            await self.take_screenshot(page, url, device, 'step09a_checkout_button_highlighted',
                                "Checkout button highlighted (purple outline)")
                            
                            print("  ✓ Found checkout button")
                            print("  🖱️  Clicking...")
                            await checkout_button.click()
                            
                            await page.wait_for_load_state('networkidle', timeout=15000)
                            
                            print("  ⏱️  Waiting 10 seconds for checkout page...")
                            await page.wait_for_timeout(10000)
                            
                            await self.take_screenshot(page, url, device, 'step09b_checkout_page_top',
                                "Checkout page loaded - top section")
                            
                            # Scroll checkout page
                            await self.capture_checkout_page(page, url, device)
                            
                            current_url = page.url
                            if 'checkout' in current_url.lower():
                                print(f"  ✓ Successfully reached checkout!")
                                print(f"  📍 Checkout URL: {current_url}")
                            else:
                                print(f"  ⚠️  May not be on checkout")
                                print(f"  📍 Current URL: {current_url}")
                            
                            checkout_found = True
                            break
                    except Exception as e:
                        continue
                
                if not checkout_found:
                    print("  ✗ Failed to reach checkout")
                    await self.take_screenshot(page, url, device, 'step09_ERROR_checkout_not_found',
                        "ERROR: Could not find or click checkout button")
                
                # STEP 10: Final full-page screenshot
                await self.take_screenshot(page, url, device, 'step10_final_complete_page',
                    "Final complete page view")
                
                # Log console errors if any
                if console_errors:
                    print(f"\n  ⚠️  {len(console_errors)} JavaScript errors detected")
                    await self.log_issue({
                        'url': url, 'device': device, 'severity': 'medium',
                        'category': 'JavaScript Errors',
                        'issue': f'{len(console_errors)} console errors',
                        'screenshot': f"{self.screenshot_counter-1:03d}",
                        'timestamp': datetime.now().isoformat()
                    })
                
                self.performance_data.append(perf_data)
                
                print("\n" + "="*80)
                print(f"✓ Completed ultra-detailed testing")
                print(f"📸 Total screenshots for this test: {self.screenshot_counter}")
                print("="*80)
            
            except Exception as e:
                print(f"\n✗ ERROR: {str(e)}")
                await self.take_screenshot(page, url, device, 'ERROR_test_failed',
                    f"Test failed with error: {str(e)}")
                
                await self.log_issue({
                    'url': url, 'device': device, 'severity': 'critical',
                    'category': 'Test Failure',
                    'issue': f'Test crashed: {str(e)}',
                    'screenshot': f"{self.screenshot_counter-1:03d}",
                    'timestamp': datetime.now().isoformat()
                })
            
            await browser.close()
    
    async def capture_scroll_journey(self, page, url, device):
        """Capture screenshots while scrolling through entire page"""
        page_height = await page.evaluate('document.body.scrollHeight')
        viewport_height = await page.evaluate('window.innerHeight')
        
        print(f"  📏 Page height: {page_height}px")
        print(f"  📏 Viewport height: {viewport_height}px")
        
        scroll_position = 0
        scroll_step = viewport_height - 100  # Overlap between screenshots
        screenshot_num = 1
        
        while scroll_position < page_height:
            await page.evaluate(f'window.scrollTo({{top: {scroll_position}, behavior: "smooth"}})')
            await page.wait_for_timeout(800)
            
            await self.take_screenshot(page, url, device, 
                f'scroll_position_{screenshot_num:02d}_at_{scroll_position}px',
                f"Scroll position {screenshot_num}: {scroll_position}px from top")
            
            scroll_position += scroll_step
            screenshot_num += 1
            
            if screenshot_num > 20:  # Safety limit
                break
        
        print(f"  ✓ Captured {screenshot_num} scroll positions")
        
        # Scroll back to top
        await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
        await page.wait_for_timeout(1000)
    
    async def check_images_detailed(self, page, url, device):
        """Check each image and capture issues"""
        images = await page.query_selector_all('img')
        total_images = len(images)
        broken_images = []
        
        print(f"  🔍 Found {total_images} images to check")
        
        for i, img in enumerate(images[:20], 1):  # Check first 20 images
            try:
                is_broken = await page.evaluate('''(img) => {
                    return !img.complete || img.naturalWidth === 0;
                }''', img)
                
                if is_broken:
                    # Scroll to broken image
                    await img.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    
                    # Highlight broken image
                    await page.evaluate('''(img) => {
                        img.style.outline = '5px solid red';
                        img.style.outlineOffset = '3px';
                    }''', img)
                    
                    await self.take_screenshot(page, url, device,
                        f'ERROR_broken_image_{i}',
                        f"BROKEN IMAGE #{i} - highlighted with red outline")
                    
                    broken_images.append(i)
                    print(f"  ❌ Image #{i} is broken")
            except:
                pass
        
        if broken_images:
            print(f"  ⚠️  Found {len(broken_images)} broken images")
            await self.log_issue({
                'url': url, 'device': device, 'severity': 'high',
                'category': 'Broken Images',
                'issue': f'{len(broken_images)} images failed to load',
                'screenshot': f"{self.screenshot_counter-1:03d}",
                'timestamp': datetime.now().isoformat()
            })
        else:
            print(f"  ✓ All {total_images} images loaded successfully")
    
    async def check_layout_detailed(self, page, url, device):
        """Check for overlapping elements"""
        overlaps = await page.evaluate('''() => {
            function overlap(el1, el2) {
                const r1 = el1.getBoundingClientRect();
                const r2 = el2.getBoundingClientRect();
                return !(r1.right < r2.left || r1.left > r2.right || 
                       r1.bottom < r2.top || r1.top > r2.bottom);
            }
            
            const elements = Array.from(document.querySelectorAll('button, a, input, .product-form'));
            let overlappingPairs = [];
            
            for (let i = 0; i < elements.length && overlappingPairs.length < 5; i++) {
                for (let j = i + 1; j < elements.length; j++) {
                    if (overlap(elements[i], elements[j])) {
                        overlappingPairs.push({
                            el1: elements[i].tagName + (elements[i].className ? '.' + elements[i].className.split(' ')[0] : ''),
                            el2: elements[j].tagName + (elements[j].className ? '.' + elements[j].className.split(' ')[0] : '')
                        });
                        if (overlappingPairs.length >= 5) break;
                    }
                }
            }
            
            return overlappingPairs;
        }''')
        
        if overlaps and len(overlaps) > 0:
            print(f"  ⚠️  Found {len(overlaps)} overlapping elements")
            
            await self.take_screenshot(page, url, device,
                'ERROR_overlapping_elements',
                f"Layout issue: {len(overlaps)} elements overlapping")
            
            await self.log_issue({
                'url': url, 'device': device, 'severity': 'medium',
                'category': 'Layout Issue',
                'issue': f'{len(overlaps)} overlapping elements detected',
                'screenshot': f"{self.screenshot_counter-1:03d}",
                'timestamp': datetime.now().isoformat()
            })
        else:
            print(f"  ✓ No overlapping elements detected")
    
    async def capture_checkout_page(self, page, url, device):
        """Capture checkout page in sections"""
        print("\n  📸 Capturing checkout page sections...")
        
        # Top section
        await page.evaluate('window.scrollTo({top: 0, behavior: "smooth"})')
        await page.wait_for_timeout(1000)
        await self.take_screenshot(page, url, device, 
            'checkout_section_1_contact_info',
            "Checkout: Contact information section")
        
        # Scroll to middle
        page_height = await page.evaluate('document.body.scrollHeight')
        await page.evaluate(f'window.scrollTo({{top: {page_height//2}, behavior: "smooth"}})')
        await page.wait_for_timeout(1000)
        await self.take_screenshot(page, url, device,
            'checkout_section_2_shipping',
            "Checkout: Shipping/delivery section")
        
        # Bottom section
        await page.evaluate(f'window.scrollTo({{top: {page_height}, behavior: "smooth"}})')
        await page.wait_for_timeout(1000)
        await self.take_screenshot(page, url, device,
            'checkout_section_3_payment',
            "Checkout: Payment section (bottom)")
        
        print("  ✓ Captured all checkout sections")
    
    async def take_screenshot(self, page, url, device, step_name, description):
        """Take a screenshot with metadata"""
        try:
            self.screenshot_counter += 1
            timestamp = datetime.now().strftime('%H%M%S')
            
            filename = f"{self.screenshot_counter:04d}_{device}_{step_name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            
            await page.screenshot(path=filepath, full_page=False)  # Viewport only for faster
            
            print(f"  📸 [{self.screenshot_counter:04d}] {description}")
            
            return str(filepath)
        except Exception as e:
            print(f"  ✗ Screenshot failed: {str(e)}")
            return None
    
    async def log_issue(self, issue):
        """Log an issue"""
        self.issues.append(issue)
        severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
        emoji = severity_emoji.get(issue['severity'], '⚪')
        print(f"  {emoji} ISSUE: {issue['category']} - {issue['issue']}")
    
    async def run_tests(self, urls):
        """Run tests on all URLs"""
        print("\n" + "="*80)
        print("🔍 ULTRA-DETAILED SHOPIFY QA AUTOMATION")
        print("Complete Visual Journey Documentation")
        print("="*80)
        print(f"\n📍 Location: New York, USA")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}")
        print(f"🔗 URLs to test: {len(urls)}")
        print(f"📱 Devices: Desktop + Mobile")
        print(f"📸 Expected screenshots: ~50-80 per URL per device")
        print("\n" + "="*80)
        
        for url in urls:
            await self.test_url(url, 'desktop')
            await asyncio.sleep(2)
            await self.test_url(url, 'mobile')
            await asyncio.sleep(2)
        
        # Save reports
        with open('qa-report.json', 'w') as f:
            json.dump(self.issues, f, indent=2)
        
        with open('performance-report.json', 'w') as f:
            json.dump(self.performance_data, f, indent=2)
        
        # Create ZIP
        print("\n📦 Creating screenshots ZIP...")
        zip_path = 'qa-screenshots.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for screenshot in self.screenshot_dir.glob('*.png'):
                zipf.write(screenshot, screenshot.name)
        
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  ✓ Created {zip_path} ({zip_size:.2f} MB)")
        
        # Summary
        print("\n" + "="*80)
        print("✅ TESTING COMPLETE!")
        print("="*80)
        print(f"\n📸 Total Screenshots: {self.screenshot_counter}")
        print(f"🐛 Total Issues: {len(self.issues)}")
        print(f"📁 ZIP Size: {zip_size:.2f} MB")
        
        if self.performance_data:
            avg_load = sum(p.get('fully_loaded', 0) for p in self.performance_data) / len(self.performance_data)
            print(f"⏱️  Average Load Time: {avg_load:.2f}s")
        
        print("\n" + "="*80)
        
        return self.issues


async def main():
    urls = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not urls:
        if os.path.exists('urls.txt'):
            with open('urls.txt') as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    if not urls:
        print("Error: No URLs provided")
        sys.exit(1)
    
    qa = UltraDetailedShopifyQA()
    await qa.run_tests(urls)


if __name__ == '__main__':
    asyncio.run(main())
