/* eslint-env browser */
/* global ConnectBoxApp */
/* eslint no-use-before-define: "off" */
var ConnectBoxApp = (function (ConnectBoxApp, $) {
  'use strict'

  var currentItem = 'home'

    // Hide the message dialog
  function hideMessageDialog () {
    $('#msg-dialog').addClass('hidden')
    $('#msg-dialog').removeClass('error')
    $('#msg-dialog #msg-title').html('')
    $('#msg-dialog #msg-body').html('')
  }

    // Show error dialog
  function showError (title, message, callback) {
    $('#msg-dialog').addClass('error')
    $('#msg-dialog #msg-title').html(title)
    $('#msg-dialog #msg-body').html(message)
    $('#msg-dialog').removeClass('hidden')

    $('#msg-dialog button').on('click', function () {
      hideMessageDialog()

      if (callback) {
        callback()
      }

      $('#msg-dialog button').off('click')
    })
  }

  function parseErrorMessage (message) {
    if (message) {
      if (Array.isArray(message)) {
        if (message.length > 0) {
          return message[message.length - 1]
        }
      } else {
        return message
      }
    }
    return 'Unknown Error'
  }

  function menuClick (event) {
    $('#' + currentItem).toggle()
    $('.active').toggleClass('active')

    currentItem = event.target.id.substring('menu_'.length)
    $(this).parent().toggleClass('active')
    $('#' + currentItem).toggle()
  }

  function clearSystemStatus () {
    $('#unmountusb_success').hide()
    $('#reboot_success').hide()
    $('#shutdown_success').hide()
    $('#reset_success').hide()
  }

  function systemLoad (event) {
    $('#' + currentItem).toggle()

    currentItem = 'system'

    $('.active').toggleClass('active')
    $('#menu_home').parent().toggleClass('active')

    clearSystemStatus()
    $('#system').toggle()
  }

  function unmountusb (event) {
    event.preventDefault()
    clearSystemStatus()

    ConnectBoxApp.api.triggerEvent('system', 'unmountusb', function (result, code, message) {
      if (result) {
        $('#unmountusb_success').show()
      } else {
        showError('Error unmounting usb', parseErrorMessage(message))
      }
    })
  }

  function reset (event) {
    event.preventDefault()
    clearSystemStatus()

    ConnectBoxApp.api.triggerEvent('system', 'reset', function (result, code, message) {
      if (result) {
        $('#reset_success').show()
      } else {
        showError('Error performing reset', parseErrorMessage(message))
      }
    })
  }

  function shutdown (event) {
    event.preventDefault()
    clearSystemStatus()

    ConnectBoxApp.api.triggerEvent('system', 'shutdown', function (result, code, message) {
      if (result) {
        $('#shutdown_success').show()
      } else {
        showError('Error performing shutdown', parseErrorMessage(message))
      }
    })
  }

  function reboot (event) {
    event.preventDefault()
    clearSystemStatus()

    ConnectBoxApp.api.triggerEvent('system', 'reboot', function (result, code, message) {
      if (result) {
        $('#reboot_success').show()
      } else {
        showError('Error performing reboot', parseErrorMessage(message))
      }
    })
  }

  function passwordLoad (event) {
    $('#' + currentItem).toggle()

    currentItem = 'password'

    $('.active').toggleClass('active')
    $('#menu_home').parent().toggleClass('active')

    $('#password').toggle()
    $('#update_password_success').hide()
  }

  function passwordSave (event) {
    event.preventDefault()

    var password = $('#input_password').val(),
      confirm = $('#input_password_confirm').val()

    if (password !== confirm) {
      alert("Password doesn't match!")
    } else {
      $('#update_password_success').hide()
      ConnectBoxApp.api.setProperty('password', $('#input_password').val(), function (result, code, message) {
        if (result) {
          $('#update_password_success').show()
        } else {
          showError('Error updating password', parseErrorMessage(message))
        }
      })
    }
  }

  function ssidLoad (event) {
    $('#' + currentItem).toggle()

    currentItem = 'ssid'

    $('.active').toggleClass('active')
    $('#menu_home').parent().toggleClass('active')

    $('#ssid').toggle()
    $('#update_ssid_success').hide()

    ConnectBoxApp.api.getProperty('ssid', function (result, code, message) {
      if (result) {
        $('#input_ssid').val(result[0])
      } else {
        showError('Error loading ssid', parseErrorMessage(message))
      }
    })
  }

  function ssidSave (event) {
    event.preventDefault()

    $('#update_ssid_success').hide()
    ConnectBoxApp.api.setProperty('ssid', $('#input_ssid').val(), function (result, code, message) {
      if (result) {
        $('#update_ssid_success').show()
      } else {
        showError('Error updating SSID', parseErrorMessage(message))
      }
    })
  }

  function channelLoad (event) {
    $('#' + currentItem).toggle()

    currentItem = 'channel'

    $('.active').toggleClass('active')
    $('#menu_home').parent().toggleClass('active')

    $('#channel').toggle()
    $('#update_channel_success').hide()

    ConnectBoxApp.api.getProperty('channel', function (result, code, message) {
      if (result) {
        $('#input_channel').val(result[0])
      } else {
        showError('Error reading channel', parseErrorMessage(message))
      }
    })
  }

  function channelSave (event) {
    event.preventDefault()

    $('#update_channel_success').hide()
    ConnectBoxApp.api.setProperty('channel', $('#input_channel').val(), function (result, code, message) {
      if (result) {
        $('#update_channel_success').show()
      } else {
        showError('Error updating channel', parseErrorMessage(message))
      }
    })
  }

  function hostnameLoad (event) {
    $('#' + currentItem).toggle()

    currentItem = 'hostname'

    $('.active').toggleClass('active')
    $('#menu_home').parent().toggleClass('active')

    $('#hostname').toggle()
    $('#update_hostname_success').hide()

    ConnectBoxApp.api.getProperty('hostname', function (result, code, message) {
      if (result) {
        $('#input_hostname').val(result[0])
      } else {
        showError('Error reading hostname', parseErrorMessage(message))
      }
    })
  }

  function hostnameSave (event) {
    event.preventDefault()

    $('#update_hostname_success').hide()
    ConnectBoxApp.api.setProperty('hostname', $('#input_hostname').val(), function (result, code, message) {
      if (result) {
        $('#update_hostname_success').show()
      } else {
        showError('Error updating hostname', parseErrorMessage(message))
      }
    })
  }

  function staticsiteLoad (event) {
    $('#' + currentItem).toggle()

    currentItem = 'staticsite'

    $('.active').toggleClass('active')
    $('#menu_home').parent().toggleClass('active')

    $('#staticsite').toggle()
    $('#update_staticsite_success').hide()

    ConnectBoxApp.api.getProperty('staticsite', function (result, code, message) {
      if (result) {
        if (result[0] === 'true') {
          $('#input_staticsite_disabled').parent().removeClass('active')
          $('#input_staticsite_enabled').parent().addClass('active')
        } else {
          $('#input_staticsite_disabled').parent().addClass('active')
          $('#input_staticsite_enabled').parent().removeClass('active')
        }
      } else {
        showError('Error reading static site settings', parseErrorMessage(message))
      }
    })
  }

  function staticsiteSave (event) {
    event.preventDefault()
    var staticEnabled = $('#input_staticsite_enabled').parent().hasClass('active')

    $('#update_staticsite_success').hide()
    ConnectBoxApp.api.setProperty('staticsite', staticEnabled, function (result, code, message) {
      if (result) {
        $('#update_staticsite_success').show()
      } else {
        showError('Error updating static site', parseErrorMessage(message))
      }
    })
  }

  function getTop10Stats (event) {
    event.preventDefault()

    window.location = '/stats.top10.json'
  }

  function getAllStats (event) {
    event.preventDefault()

    window.location = '/stats.json'
  }

  ConnectBoxApp.ui = {
    init: function () {
      var selectedMenuItem = '#menu_home'
      var selectedItem = '#home'
      if (location.hash) {
        currentItem = location.hash.substring(1)
        selectedMenuItem = '#menu_' + currentItem
        selectedItem = location.hash
      }
      $(selectedMenuItem).parent().toggleClass('active')
      $(selectedItem).toggle()

      $('#menu_home').on('click', menuClick)
      $('#menu_about').on('click', menuClick)
      $('#menu_contact').on('click', menuClick)
      $('#menu_ssid').on('click', ssidLoad)
      $('#form_ssid').on('submit', ssidSave)
      $('#menu_channel').on('click', channelLoad)
      $('#form_channel').on('submit', channelSave)
      $('#menu_hostname').on('click', hostnameLoad)
      $('#form_hostname').on('submit', hostnameSave)
      $('#menu_staticsite').on('click', staticsiteLoad)
      $('#form_staticsite').on('submit', staticsiteSave)
      $('#menu_password').on('click', passwordLoad)
      $('#form_password').on('submit', passwordSave)
      $('#menu_system').on('click', systemLoad)
      $('#form_unmountusb').on('submit', unmountusb)
      $('#form_shutdown').on('submit', shutdown)
      $('#form_reboot').on('submit', reboot)
      $('#form_reset').on('submit', reset)
      $('#menu_top10_stats').on('click', getTop10Stats)
      $('#menu_all_stats').on('click', getAllStats)
    }
  }

  return ConnectBoxApp
}(ConnectBoxApp || {}, jQuery))
