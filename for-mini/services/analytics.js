/* 轻量匿名事件上报：仅在宿主支持 wx.reportEvent 时尽力上报，不传用户身份与自由文本 */

function safeReport(eventName, payload) {
  try {
    if (typeof wx === 'undefined' || !wx || typeof wx.reportEvent !== 'function') {
      return false
    }
    var clean = {}
    if (payload && typeof payload === 'object') {
      Object.keys(payload).forEach(function (key) {
        var val = payload[key]
        if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
          clean[key] = val
        }
      })
    }
    wx.reportEvent(String(eventName), clean)
    return true
  } catch (err) {
    return false
  }
}

module.exports = {
  track: safeReport
}
