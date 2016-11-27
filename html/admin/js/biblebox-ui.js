var BibleBoxApp = (function (BibleBoxApp, $) {
    'use strict';
    
    var currentItem = 'home';

    // //Hide the message dialog
    // function hideMessageDialog() {
    //     $("#msg-dialog").addClass("hidden");
    //     $("#msg-dialog").removeClass("error");
    //     $("#msg-dialog #msg-title").html('');
    //     $("#msg-dialog #msg-body").html('');
    // }
    
    // //Show error dialog
    // function showError(title, message, callback) {
    //     $("#msg-dialog").addClass("error");
    //     $("#msg-dialog #msg-title").html(title);
    //     $("#msg-dialog #msg-body").html(message);
    //     $("#msg-dialog").removeClass("hidden");
                
    //     $("#msg-dialog button").on('click', function () {
    //         hideMessageDialog();
            
    //         if (callback) {
    //             callback();
    //         }
            
    //         $("#msg-dialog button").off('click');
    //     });
    // }

    function menuClick(event) {
        $('#' + currentItem).toggle();
        $('.active').toggleClass('active');

        currentItem = event.target.id.substring('menu_'.length);
        $(this).parent().toggleClass('active');
        $('#' + currentItem).toggle();
    }

    function clearSystemStatus() {
        $('#unmountusb_success').hide();
        $('#unmountusb_failure').hide();
        $('#reboot_success').hide();
        $('#reboot_failure').hide();
        $('#shutdown_success').hide();
        $('#shutdown_failure').hide();
    }

    function systemLoad(event) {
        $('#' + currentItem).toggle();

        currentItem = 'system';

        $('.active').toggleClass('active');
        $('#menu_home').parent().toggleClass('active');

        clearSystemStatus();
        $('#system').toggle();
    }

    function unmountusb(event) {
        event.preventDefault();
        clearSystemStatus();

        BibleBoxApp.api.triggerEvent('system', 'unmountusb', function(result, code, message) {
            if (result !== undefined) {
                $('#unmountusb_success').show();
            } else {
                $('#unmountusb_failure').show();
            }
        });
    }

    function shutdown(event) {
        event.preventDefault();
        clearSystemStatus();

        BibleBoxApp.api.triggerEvent('system', 'shutdown', function(result, code, message) {
            if (result !== undefined) {
                $('#shutdown_success').show();
            } else {
                $('#shutdown_failure').show();
            }
        });
    }

    function reboot(event) {
        event.preventDefault();
        clearSystemStatus();

        BibleBoxApp.api.triggerEvent('system', 'reboot', function(result, code, message) {
            if (result !== undefined) {
                $('#reboot_success').show();
            } else {
                $('#reboot_failure').show();
            }
        });
    }

    function passwordLoad(event) {
        $('#' + currentItem).toggle();

        currentItem = 'password';

        $('.active').toggleClass('active');
        $('#menu_home').parent().toggleClass('active');

        $('#password').toggle();
        $('#update_password_success').hide();
        $('#update_password_failure').hide();
    }

    function passwordSave(event) {
        event.preventDefault();

        var password = $('#input_password').val(),
            confirm = $('#input_password_confirm').val();

        if (password !== confirm) {
            alert("Password doesn't match!");
        } else {
            BibleBoxApp.api.setProperty('password', $('#input_password').val(), function(result, code, message) {
                if (result !== undefined) {
                    $('#update_password_success').show();
                } else {
                    $('#update_password_failure').show();
                }
            });
        }
    }

    function ssidLoad(event) {
        $('#' + currentItem).toggle();

        currentItem = 'ssid';

        $('.active').toggleClass('active');
        $('#menu_home').parent().toggleClass('active');

        $('#ssid').toggle();
        $('#update_ssid_success').hide();
        $('#update_ssid_failure').hide();

        BibleBoxApp.api.getProperty('ssid', function (result, code, message) {
            if (result !== undefined) {
                $('#input_ssid').val(result[0]);
            } else {
                //TODO display a proper error message
            }
        });
    }

    function ssidSave(event) {
        event.preventDefault();

        BibleBoxApp.api.setProperty('ssid', $('#input_ssid').val(), function(result, code, message) {
            if (result !== undefined) {
                $('#update_ssid_success').show();
            } else {
                $('#update_ssid_failure').show();
            }
        });
    }

    function channelLoad(event) {
        $('#' + currentItem).toggle();

        currentItem = 'channel';

        $('.active').toggleClass('active');
        $('#menu_home').parent().toggleClass('active');

        $('#channel').toggle();
        $('#update_channel_success').hide();
        $('#update_channel_failure').hide();

        BibleBoxApp.api.getProperty('channel', function (result, code, message) {
            if (result !== undefined) {
                $('#input_channel').val(result[0]);
            } else {
                //TODO display a proper error message
            }
        });
    }

    function channelSave(event) {
        event.preventDefault();

        BibleBoxApp.api.setProperty('channel', $('#input_channel').val(), function(result, code, message) {
            if (result !== undefined) {
                $('#update_channel_success').show();
            } else {
                $('#update_channel_failure').show();
            }
        });
    }

    BibleBoxApp.ui = {
        init: function () {
            var selectedMenuItem = '#menu_home';
            var selectedItem = '#home';
            if (location.hash) {
                currentItem = location.hash.substring(1);
                selectedMenuItem = '#menu_' + currentItem;
                selectedItem = location.hash;
            }
            $(selectedMenuItem).parent().toggleClass('active');
            $(selectedItem).toggle();

            $('#menu_home').on('click', menuClick);
            $('#menu_about').on('click', menuClick);
            $('#menu_contact').on('click', menuClick);
            $('#menu_ssid').on('click', ssidLoad);
            $('#form_ssid').on('submit', ssidSave);
            $('#menu_channel').on('click', channelLoad);
            $('#form_channel').on('submit', channelSave);
            $('#menu_password').on('click', passwordLoad);
            $('#form_password').on('submit', passwordSave);
            $('#menu_system').on('click', systemLoad);
            $('#form_unmountusb').on('submit', unmountusb);
            $('#form_shutdown').on('submit', shutdown);
            $('#form_reboot').on('submit', reboot);
            //$("#form_password").on('submit', passwordSave);

            // //handler to load more transactions on scroll
            // $('#transactions-list-container').on('scroll', handleTransactionListScroll);

            // //Login button handler
            // $('#login-button').on('click', doLogin);

            // //Login on enter key
            // $('#login-dialog').on('keydown', function (evt) {
            //     if (evt.which === 13) {
            //         evt.preventDefault();
            //         doLogin();
            //     }
            // });

            // //Logout button
            // $('#logout-button').on('click', doLogout);

            // //Open txn create dialog
            // $("#txn-open-dialog-button").on('click', function () {
            //     $('#txn-create-dialog').removeClass('hidden');
            // });

            // //Create txn button
            // $('#txn-create-button').on('click', doTxnCreate);

            // //Cancel create txn button
            // $('#txn-create-cancel-button').on('click', function () {
            //     $('#txn-create-dialog').addClass('hidden');
            // });

            // //Default date
            // $("#txn-date-input").val(BibleBoxApp.util.formatDate());

            // if (BibleBoxApp.api.isAuthenticated()) {
            //     showTransactions();
            // } else {
            //     $('.loading').hide();
            //     showLogin();
            // }
        }
    };
    
    return BibleBoxApp;
}(BibleBoxApp || {}, jQuery));