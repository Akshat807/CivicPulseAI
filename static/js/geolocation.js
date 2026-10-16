
(function () {
    const button = document.getElementById("getLocationBtn");
    const message = document.getElementById("locationMessage");
    const latitudeInput = document.getElementById("latitude");
    const longitudeInput = document.getElementById("longitude");
    const addressInput = document.getElementById("location_address");

    // GPS controls may not exist on every page.
    if (!button || !message || !latitudeInput || !longitudeInput) {
        return;
    }

    function showLocationMessage(text, type) {
        message.textContent = text;
        message.className = "location-message";

        if (type) {
            message.classList.add(type);
        }
    }

    button.addEventListener("click", function () {
        if (!navigator.geolocation) {
            showLocationMessage(
                "This browser does not support GPS. Enter an address or landmark manually.",
                "error"
            );
            return;
        }

        button.disabled = true;
        button.textContent = "Getting your location...";

        showLocationMessage(
            "Requesting your location. Please respond to the browser permission prompt."
        );

        navigator.geolocation.getCurrentPosition(
            async function (position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                const accuracy = position.coords.accuracy;

                latitudeInput.value = latitude;
                longitudeInput.value = longitude;

                showLocationMessage(
                    "✓ Location captured. Reported GPS accuracy is approximately " +
                    Math.round(accuracy) +
                    " metres. Looking up the address...",
                    "success"
                );

                // Automatically fill the address if the citizen
                // has not already entered one manually.
                if (addressInput && !addressInput.value.trim()) {
                    try {
                        const response = await fetch(
                            `/reverse-geocode?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`
                        );

                        const result = await response.json();

                        if (response.ok && result.success && result.address) {
                            addressInput.value = result.address;

                            showLocationMessage(
                                "✓ GPS location captured and address filled automatically. Check that it matches the issue location.",
                                "success"
                            );
                        } else {
                            showLocationMessage(
                                "✓ GPS location captured, but address lookup failed. Please enter the address manually.",
                                "error"
                            );
                        }
                    } catch (error) {
                        showLocationMessage(
                            "✓ GPS location captured, but address lookup is unavailable. Please enter the address manually.",
                            "error"
                        );
                    }
                } else {
                    showLocationMessage(
                        "✓ GPS location captured. Your manually entered address was preserved. Check that it matches the issue location.",
                        "success"
                    );
                }

                button.disabled = false;
                button.textContent = "✓ Location Captured";
            },
            function (error) {
                latitudeInput.value = "";
                longitudeInput.value = "";

                let errorMessage =
                    "Could not get your location. You can enter an address manually or continue without GPS.";

                if (error.code === error.PERMISSION_DENIED) {
                    errorMessage =
                        "Location permission was denied. Allow it in your browser settings or enter the address manually.";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    errorMessage =
                        "Your location is currently unavailable. Try again or enter the address manually.";
                } else if (error.code === error.TIMEOUT) {
                    errorMessage =
                        "The location request timed out. Try again or enter the address manually.";
                }

                showLocationMessage(errorMessage, "error");

                button.disabled = false;
                button.textContent = "📍 Try Again";
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    });
})();
