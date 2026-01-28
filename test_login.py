from browser.driver import Driver
from browser.yolo_reader import YOLOReader
from time import sleep

driver = Driver()
driver.get("https://facebook.com", e_wait=5)

# 🔍 DEBUG: Kiểm tra viewport
viewport = driver.current_page.viewport_size
print(f"📐 Viewport size: {viewport}")
# Lấy DPR
dpr =  driver.current_page.evaluate("window.devicePixelRatio")
driver.click_mouse(10, 10)

# Screenshot viewport
img_bytes = driver.screenshot(path="")


yolo = YOLOReader("E:\\asfy\\facebook\\tool_playwright\\vision\\models\\login.pt", dpr=dpr)
result = yolo.detect(img_bytes=img_bytes)
print('result: ', result)
# ===== CÁCH 3: Đọc tất cả text =====
all_texts = yolo.get_all_text(img_bytes)
print(f"📋 Tất cả text: {all_texts}")

# for result in results:
mat_khau = result['mat_khau']
nut_dang_nhap = result['nut_dang_nhap']
tai_khoan = result['tai_khoan']

# 🔍 DEBUG: In tọa độ
print(f"\n📍 Tọa độ tài khoản: ({tai_khoan['center_x']}, {tai_khoan['center_y']})")
print(f"📍 Tọa độ mật khẩu: ({mat_khau['center_x']}, {mat_khau['center_y']})")
print(f"📍 Tọa độ nút đăng nhập: ({nut_dang_nhap['center_x']}, {nut_dang_nhap['center_y']})")

# 🔍 DEBUG: Vẽ border lên element để xem Playwright có focus đúng không
driver.current_page.evaluate(f"""
    const div = document.createElement('div');
    div.style.position = 'fixed';
    div.style.left = '{mat_khau['x1']}px';
    div.style.top = '{mat_khau['y1']}px';
    div.style.width = '{mat_khau['width']}px';
    div.style.height = '{mat_khau['height']}px';
    div.style.border = '3px solid red';
    div.style.zIndex = '99999';
    div.style.pointerEvents = 'none';
    document.body.appendChild(div);
""")

sleep(2)  # Xem có border đỏ xuất hiện đúng vị trí không

# Test click thủ công trước
print("\n🖱️ Test click vào tài khoản...")
driver.current_page.mouse.click(mat_khau['center_x'], mat_khau['center_y'])
sleep(1)

# 🔍 DEBUG: Kiểm tra xem có element nào được focus không
focused = driver.current_page.evaluate("document.activeElement.tagName")
print(f"✅ Element đang focus: {focused}")

# Thử nhập text
print("⌨️ Test nhập text...")
driver.send_keys("test123")
sleep(2)

# Kiểm tra text có được nhập không
input_value = driver.current_page.evaluate("""
    document.activeElement.value
""")
print(f"📝 Giá trị đã nhập: '{input_value}'")

sleep(10)