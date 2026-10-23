import { useEffect, useState, type FormEvent } from "react";
import "./App.css";

type Movie = {
  id: number;
  title: string;
  genre: string;
  language: string;
  duration_minutes: number;
  description: string;
  poster_url: string;
};

type User = {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
};

type Dashboard = {
  message: string;
  admin_email: string;
  statistics: {
    total_users: number;
    total_movies: number;
  };
};

type Showtime = {
  id: number;
  movie_id: number;
  movie_title: string;
  cinema_id: number;
  cinema_name: string;
  city: string;
  screen_id: number;
  screen_name: string;
  total_seats: number;
  starts_at: string;
  ticket_price_paise: number;
};

type Seat = {
  seat_number: number;
  status: "available" | "booked";
};

type SeatAvailability = {
  showtime_id: number;
  total_seats: number;
  available_seats: number;
  booked_seats: number;
  seats: Seat[];
};

type Booking = {
  id: number;
  user_id: number;
  showtime_id: number;
  seat_number: number;
  status: "pending_payment" | "confirmed" | "cancelled";
  booked_at: string;
};

type SandboxPaymentResponse = {
  id: number;
  booking_id: number;
  amount_rupees: string;
  currency: string;
  provider: string;
  status: "succeeded" | "failed";
  reference: string;
  created_at: string;
};

type AuthMode = "login" | "register";

const TOKEN_KEY = "cinebook_access_token";

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(path, { ...options, headers });

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Keep the HTTP status message.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

function formatPrice(paise: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);
}

function App() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loadingMovies, setLoadingMovies] = useState(true);
  const [movieError, setMovieError] = useState("");

  const [token, setToken] = useState(
    () => sessionStorage.getItem(TOKEN_KEY) ?? "",
  );
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(() => Boolean(sessionStorage.getItem(TOKEN_KEY)));
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [showAuth, setShowAuth] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [notice, setNotice] = useState("");

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashboardBusy, setDashboardBusy] = useState(false);
  const [dashboardError, setDashboardError] = useState("");

  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [showtimes, setShowtimes] = useState<Showtime[]>([]);
  const [showtimesBusy, setShowtimesBusy] = useState(false);
  const [showtimesError, setShowtimesError] = useState("");
  const [selectedShowtime, setSelectedShowtime] = useState<Showtime | null>(null);

  const [seatData, setSeatData] = useState<SeatAvailability | null>(null);
  const [seatsBusy, setSeatsBusy] = useState(false);
  const [selectedSeat, setSelectedSeat] = useState<number | null>(null);
  const [bookingBusy, setBookingBusy] = useState(false);
  const [pendingPaymentBooking, setPendingPaymentBooking] = useState<Booking | null>(null);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [paymentResult, setPaymentResult] = useState<SandboxPaymentResponse | null>(null);

  const [bookings, setBookings] = useState<Booking[]>([]);
  const [bookingsBusy, setBookingsBusy] = useState(false);
  const [bookingsError, setBookingsError] = useState("");
  const [showBookings, setShowBookings] = useState(false);

  useEffect(() => {
    let active = true;

    fetch("/api/movies")
      .then((response) => {
        if (!response.ok) throw new Error("Could not load movies.");
        return response.json() as Promise<Movie[]>;
      })
      .then((data) => {
        if (active) setMovies(data);
      })
      .catch(() => {
        if (active) {
          setMovieError("Unable to load movies. Check that CineBook services are running.");
        }
      })
      .finally(() => {
        if (active) setLoadingMovies(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    if (!token) {
      return;
    }

    apiRequest<User>("/api/auth/me", { method: "GET" }, token)
      .then((profile) => {
        if (active) setUser(profile);
      })
      .catch(() => {
        if (active) {
          sessionStorage.removeItem(TOKEN_KEY);
          setToken("");
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    setNotice("");
    setAuthBusy(true);

    try {
      if (authMode === "register") {
        await apiRequest<User>("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({
            full_name: fullName.trim(),
            email: email.trim().toLowerCase(),
            password,
          }),
        });

        setNotice("Account created. Sign in with your new credentials.");
        setAuthMode("login");
        setPassword("");
        return;
      }

      const result = await apiRequest<{ access_token: string; token_type: string }>(
        "/api/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            email: email.trim().toLowerCase(),
            password,
          }),
        },
      );

      sessionStorage.setItem(TOKEN_KEY, result.access_token);
      setToken(result.access_token);
      setPassword("");
      setShowAuth(false);
      setNotice("Welcome back to CineBook!");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setAuthBusy(false);
    }
  }

  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken("");
    setUser(null);
    setDashboard(null);
    setDashboardError("");
    setBookings([]);
    setShowBookings(false);
    setNotice("You have signed out.");
  }

  async function loadAdminDashboard() {
    if (!token || user?.role !== "admin") return;

    setDashboardBusy(true);
    setDashboardError("");
    setDashboard(null);

    try {
      const data = await apiRequest<Dashboard>(
        "/api/admin/dashboard",
        { method: "GET" },
        token,
      );
      setDashboard(data);
    } catch (error) {
      setDashboardError(error instanceof Error ? error.message : "Could not load dashboard.");
    } finally {
      setDashboardBusy(false);
    }
  }

  async function openMovieBooking(movie: Movie) {
    setSelectedMovie(movie);
    setSelectedShowtime(null);
    setSeatData(null);
    setSelectedSeat(null);
    setShowtimes([]);
    setShowtimesError("");
    setShowBookings(false);
    setNotice("");
    setShowtimesBusy(true);

    try {
      const data = await apiRequest<Showtime[]>(
        `/api/showtimes?movie_id=${movie.id}`,
      );
      setShowtimes(data);
    } catch (error) {
      setShowtimesError(error instanceof Error ? error.message : "Could not load showtimes.");
    } finally {
      setShowtimesBusy(false);
    }

    window.setTimeout(() => {
      document.getElementById("booking-panel")?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }

  async function chooseShowtime(showtime: Showtime) {
    setSelectedShowtime(showtime);
    setSelectedSeat(null);
    setSeatData(null);
    setNotice("");
    setSeatsBusy(true);

    try {
      const data = await apiRequest<SeatAvailability>(
        `/api/showtimes/${showtime.id}/seats`,
      );
      setSeatData(data);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not load seats.");
    } finally {
      setSeatsBusy(false);
    }
  }

  async function confirmBooking() {
    if (!user || !token) {
      setAuthMode("login");
      setAuthError("");
      setShowAuth(true);
      setNotice("Please sign in before booking a seat.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    if (user.role !== "customer") {
      setNotice("Ticket booking is available to customer accounts.");
      return;
    }

    if (!selectedShowtime || selectedSeat === null) return;

    setBookingBusy(true);
    setNotice("");
    setPaymentResult(null);

    try {
      const booking = await apiRequest<Booking>(
        "/api/bookings",
        {
          method: "POST",
          body: JSON.stringify({
            showtime_id: selectedShowtime.id,
            seat_number: selectedSeat,
          }),
        },
        token,
      );

      setPendingPaymentBooking(booking);
      setNotice(
        `Booking #${booking.id} is reserved for payment. Complete sandbox checkout within 10 minutes.`,
      );

      const refreshed = await apiRequest<SeatAvailability>(
        `/api/showtimes/${selectedShowtime.id}/seats`,
      );
      setSeatData(refreshed);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not create booking.");
      try {
        const refreshed = await apiRequest<SeatAvailability>(
          `/api/showtimes/${selectedShowtime.id}/seats`,
        );
        setSeatData(refreshed);
      } catch {
        // Keep the original booking error.
      }
    } finally {
      setBookingBusy(false);
    }
  }

  async function simulatePayment(outcome: "success" | "failure") {
    if (!token || !pendingPaymentBooking || paymentBusy) return;

    setPaymentBusy(true);
    setNotice("");
    setPaymentResult(null);

    try {
      const result = await apiRequest<SandboxPaymentResponse>(
        "/api/payments/sandbox",
        {
          method: "POST",
          body: JSON.stringify({
            booking_id: pendingPaymentBooking.id,
            outcome,
          }),
        },
        token,
      );

      setPaymentResult(result);
      setPendingPaymentBooking(null);
      setSelectedSeat(null);
      setNotice(
        result.status === "succeeded"
          ? `Payment successful. Booking #${result.booking_id} is confirmed.`
          : `Sandbox payment failed. Booking #${result.booking_id} was cancelled.`,
      );

      if (selectedShowtime) {
        const refreshed = await apiRequest<SeatAvailability>(
          `/api/showtimes/${selectedShowtime.id}/seats`,
        );
        setSeatData(refreshed);
      }

      if (showBookings) await loadMyBookings();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Payment could not be completed. Check booking status before retrying.",
      );

      if (selectedShowtime) {
        try {
          const refreshed = await apiRequest<SeatAvailability>(
            `/api/showtimes/${selectedShowtime.id}/seats`,
          );
          setSeatData(refreshed);
        } catch {
          // Keep the original payment error.
        }
      }
    } finally {
      setPaymentBusy(false);
    }
  }
  async function loadMyBookings() {
    if (!token) return;

    setBookingsBusy(true);
    setBookingsError("");

    try {
      const data = await apiRequest<Booking[]>(
        "/api/bookings/me",
        { method: "GET" },
        token,
      );
      setBookings(data);
      setShowBookings(true);
    } catch (error) {
      setBookingsError(error instanceof Error ? error.message : "Could not load bookings.");
    } finally {
      setBookingsBusy(false);
    }
  }

  async function cancelBooking(bookingId: number) {
    if (!token) return;

    setNotice("");

    try {
      await apiRequest<Booking>(
        `/api/bookings/${bookingId}/cancel`,
        { method: "POST" },
        token,
      );
      setNotice("Booking cancelled. The seat is available again.");
      await loadMyBookings();

      if (selectedShowtime) {
        const refreshed = await apiRequest<SeatAvailability>(
          `/api/showtimes/${selectedShowtime.id}/seats`,
        );
        setSeatData(refreshed);
      }
    } catch (error) {
      setBookingsError(error instanceof Error ? error.message : "Could not cancel booking.");
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CineBook home">
          <span className="brand-mark">C</span>
          <span>Cine<span>Book</span></span>
        </a>

        <nav className="nav-links">
          <a className="nav-active" href="#movies">Movies</a>
          <a href="#experience">Experience</a>
          {user?.role === "admin" && (
            <button className="nav-button" onClick={loadAdminDashboard}>
              Admin dashboard
            </button>
          )}
          {user?.role === "customer" && (
            <button className="nav-button" onClick={loadMyBookings}>
              My bookings
            </button>
          )}
        </nav>

        <div className="account-actions">
          {authLoading ? (
            <span className="account-label">Checking session...</span>
          ) : user ? (
            <>
              <span className="account-label">
                Hi, {user.full_name}
                {user.role === "admin" && <span className="role-pill">ADMIN</span>}
              </span>
              <button className="signin-button" onClick={logout}>
                Sign out <span aria-hidden="true">&gt;</span>
              </button>
            </>
          ) : (
            <button
              className="signin-button"
              onClick={() => {
                setAuthMode("login");
                setAuthError("");
                setNotice("");
                setShowAuth(true);
              }}
            >
              Sign in <span aria-hidden="true">&gt;</span>
            </button>
          )}
        </div>
      </header>

      <main>
        {showAuth && !user && (
          <section className="auth-section" aria-labelledby="auth-title">
            <div className="auth-card">
              <div className="eyebrow">YOUR CINEBOOK ACCOUNT</div>
              <h2 id="auth-title">
                {authMode === "login" ? "Welcome back." : "Join the experience."}
              </h2>
              <p className="auth-description">
                {authMode === "login"
                  ? "Sign in to continue your movie journey."
                  : "Create your account and get ready for movie night."}
              </p>

              {authError && <div className="state-message error-message" role="alert">{authError}</div>}
              {notice && <div className="state-message success-message" role="status">{notice}</div>}

              <form className="auth-form" onSubmit={handleAuthSubmit}>
                {authMode === "register" && (
                  <label>
                    Full name
                    <input
                      autoComplete="name"
                      required
                      minLength={2}
                      maxLength={120}
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      placeholder="Your full name"
                    />
                  </label>
                )}

                <label>
                  Email address
                  <input
                    type="email"
                    autoComplete="email"
                    required
                    maxLength={255}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                  />
                </label>

                <label>
                  Password
                  <input
                    type="password"
                    autoComplete={authMode === "login" ? "current-password" : "new-password"}
                    required
                    minLength={authMode === "register" ? 12 : 1}
                    maxLength={128}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={authMode === "register" ? "At least 12 characters" : "Enter your password"}
                  />
                </label>

                <button className="primary-button auth-submit" disabled={authBusy}>
                  {authBusy ? "Please wait..." : authMode === "login" ? "Sign in" : "Create account"}
                  <span aria-hidden="true">&gt;</span>
                </button>
              </form>

              <div className="auth-switch">
                {authMode === "login" ? "New to CineBook?" : "Already have an account?"}
                <button
                  onClick={() => {
                    setAuthMode(authMode === "login" ? "register" : "login");
                    setAuthError("");
                    setNotice("");
                  }}
                >
                  {authMode === "login" ? "Create account" : "Sign in"}
                </button>
              </div>

              <button
                className="text-button"
                onClick={() => {
                  setShowAuth(false);
                  setAuthError("");
                  setNotice("");
                }}
              >
                Back to movies
              </button>
            </div>
          </section>
        )}

        {notice && !showAuth && (
          <div className="notice-banner" role="status">{notice}</div>
        )}

        {user?.role === "admin" && (
          <section className="admin-section" aria-labelledby="admin-title">
            <div className="section-heading">
              <div>
                <div className="eyebrow">RESTRICTED AREA | ADMINISTRATOR</div>
                <h2 id="admin-title">Admin dashboard<span>.</span></h2>
              </div>
              <button className="book-button" onClick={loadAdminDashboard} disabled={dashboardBusy}>
                {dashboardBusy ? "Loading..." : "Refresh statistics"}
              </button>
            </div>

            {dashboardError && <div className="state-message error-message" role="alert">{dashboardError}</div>}

            {dashboard && (
              <div className="dashboard-grid">
                <article className="dashboard-card">
                  <span>Total users</span>
                  <strong>{dashboard.statistics.total_users}</strong>
                  <small>Registered accounts</small>
                </article>
                <article className="dashboard-card">
                  <span>Total movies</span>
                  <strong>{dashboard.statistics.total_movies}</strong>
                  <small>Movies in the catalogue</small>
                </article>
                <article className="dashboard-card">
                  <span>Signed in as</span>
                  <strong className="dashboard-email">{dashboard.admin_email}</strong>
                  <small>Administrator account</small>
                </article>
              </div>
            )}

            {!dashboard && !dashboardError && !dashboardBusy && (
              <p className="auth-description">Select Refresh statistics to load the latest dashboard figures.</p>
            )}
          </section>
        )}

        {showBookings && user?.role === "customer" && (
          <section className="booking-panel" aria-labelledby="my-bookings-title">
            <div className="section-heading">
              <div>
                <div className="eyebrow">YOUR CINEBOOK ACCOUNT</div>
                <h2 id="my-bookings-title">My bookings<span>.</span></h2>
              </div>
              <button className="book-button" onClick={() => setShowBookings(false)}>
                Close
              </button>
            </div>
            {bookingsBusy && <p className="auth-description">Loading your bookings...</p>}
            {bookingsError && <div className="state-message error-message">{bookingsError}</div>}

            {!bookingsBusy && !bookingsError && bookings.length === 0 && (
              <p className="auth-description">You have no bookings yet. Choose a movie to get started.</p>
            )}

            <div className="booking-history-list">
              {bookings.map((booking) => {
                const showtime = showtimes.find((item) => item.id === booking.showtime_id);
                return (
                  <article className="history-card" key={booking.id}>
                    <div>
                      <strong>{showtime?.movie_title ?? `Showtime #${booking.showtime_id}`}</strong>
                      <p>Seat {booking.seat_number} | {booking.status}</p>
                      {showtime && <p>{formatDateTime(showtime.starts_at)}</p>}
                    </div>
                    {booking.status === "confirmed" && (
                      <button className="book-button" onClick={() => cancelBooking(booking.id)}>
                        Cancel booking
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        )}

        <section className="hero">
          <div className="hero-content">
            <div className="eyebrow"><span className="live-dot" />YOUR NEXT MOVIE NIGHT STARTS HERE</div>
            <h1>Big stories.<br /><span>Big-screen</span> moments.</h1>
            <p>Discover your next favourite film. Choose your seats. Make every movie night count.</p>
            <a className="primary-button" href="#movies">Explore movies &gt;</a>
            <div className="hero-meta">
              <span><strong>01</strong> Discover</span>
              <span><strong>02</strong> Choose seats</span>
              <span><strong>03</strong> Enjoy the show</span>
            </div>
          </div>

          <div className="hero-art" aria-label="Decorative cinematic spotlight">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="film-reel">C<span>*</span></div>
            <div className="hero-caption">
              <span>YOUR SEAT IS WAITING</span>
              <strong>Lights. Camera. CineBook.</strong>
            </div>
          </div>
        </section>

        <section className="movie-section" id="movies">
          <div className="section-heading">
            <div>
              <div className="eyebrow">CURATED FOR YOUR NEXT NIGHT OUT</div>
              <h2>Now showing<span>.</span></h2>
            </div>
            <div className="catalogue-label"><span className="catalogue-dot" />MOVIE COLLECTION</div>
          </div>
          {loadingMovies && <div className="state-message">Loading the latest movies...</div>}
          {movieError && <div className="state-message error-message">{movieError}</div>}
          {!loadingMovies && !movieError && movies.length === 0 && (
            <div className="state-message">No movies are available right now.</div>
          )}

          <div className="movie-grid">
            {movies.map((movie, index) => (
              <article className="movie-card" key={movie.id}>
                <div className="poster-wrap">
                  <img className="poster" src={movie.poster_url} alt={`${movie.title} poster`} loading="lazy" />
                  <span className="poster-index">{String(index + 1).padStart(2, "0")}</span>
                  <span className="poster-tag">{movie.language}</span>
                </div>
                <div className="movie-info">
                  <div className="movie-genre">{movie.genre}</div>
                  <h3>{movie.title}</h3>
                  <p className="movie-description">{movie.description}</p>
                  <div className="movie-footer">
                    <span>{movie.duration_minutes} min</span>
                    <button className="book-button" onClick={() => openMovieBooking(movie)}>
                      Book tickets <span aria-hidden="true">&gt;</span>
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        {selectedMovie && (
          <section className="booking-panel" id="booking-panel" aria-labelledby="booking-title">
            <div className="section-heading">
              <div>
                <div className="eyebrow">CHOOSE YOUR CINEMA EXPERIENCE</div>
                <h2 id="booking-title">{selectedMovie.title}<span>.</span></h2>
                <p className="auth-description">{selectedMovie.language} | {selectedMovie.duration_minutes} minutes</p>
              </div>
              <button
                className="book-button"
                onClick={() => {
                  setSelectedMovie(null);
                  setSelectedShowtime(null);
                  setSeatData(null);
                  setSelectedSeat(null);
                }}
              >
                Close
              </button>
            </div>
            {showtimesBusy && <div className="state-message">Finding upcoming showtimes...</div>}
            {showtimesError && <div className="state-message error-message">{showtimesError}</div>}
            {!showtimesBusy && !showtimesError && showtimes.length === 0 && (
              <div className="state-message">No upcoming showtimes are available for this movie.</div>
            )}

            {showtimes.length > 0 && (
              <>
                <h3 className="booking-subtitle">1. Select a showtime</h3>
                <div className="showtime-grid">
                  {showtimes.map((showtime) => (
                    <button
                      className={`showtime-option ${selectedShowtime?.id === showtime.id ? "selected" : ""}`}
                      key={showtime.id}
                      onClick={() => chooseShowtime(showtime)}
                    >
                      <strong>{formatDateTime(showtime.starts_at)}</strong>
                      <span>{showtime.cinema_name} | {showtime.city}</span>
                      <span>{showtime.screen_name}</span>
                      <b>{formatPrice(showtime.ticket_price_paise)} / ticket</b>
                    </button>
                  ))}
                </div>
              </>
            )}

            {selectedShowtime && (
              <div className="seat-section">
                <h3 className="booking-subtitle">2. Choose your seat</h3>
                <p className="auth-description">
                  {selectedShowtime.screen_name} | {seatData?.available_seats ?? 0} seats available
                </p>
                    {seatsBusy && <div className="state-message">Loading seat availability...</div>}

                {seatData && (
                  <>
                    <div className="screen-indicator">SCREEN</div>
                    <div className="seat-grid" aria-label="Cinema seat selection">
                      {seatData.seats.map((seat) => {
                        const isSelected = selectedSeat === seat.seat_number;
                        return (
                          <button
                            key={seat.seat_number}
                            className={`seat ${seat.status === "booked" ? "seat-booked" : "seat-available"} ${isSelected ? "seat-selected" : ""}`}
                            disabled={seat.status === "booked" || bookingBusy}
                            aria-label={`Seat ${seat.seat_number}, ${seat.status}${isSelected ? ", selected" : ""}`}
                            aria-pressed={isSelected}
                            onClick={() => setSelectedSeat(isSelected ? null : seat.seat_number)}
                          >
                            {seat.seat_number}
                          </button>
                        );
                      })}
                    </div>

                    <div className="seat-legend">
                      <span><i className="legend-available" /> Available</span>
                      <span><i className="legend-selected" /> Selected</span>
                      <span><i className="legend-booked" /> Booked</span>
                    </div>

                    {!pendingPaymentBooking && (
                      <div className="booking-summary">
                        <div>
                          <span className="auth-description">Selected seat</span>
                          <strong>{selectedSeat === null ? "Select a seat to see the total" : formatPrice(selectedShowtime.ticket_price_paise)}</strong>
                        </div>
                        <div>
                          <span className="auth-description">Total</span>
                          <strong>{selectedSeat === null ? "Select a seat to see the total" : formatPrice(selectedShowtime.ticket_price_paise)}</strong>
                        </div>
                        <button
                          className="primary-button"
                          disabled={selectedSeat === null || bookingBusy || seatsBusy}
                          onClick={confirmBooking}
                        >
                    {bookingBusy ? "Creating reservation..." : user ? "Continue to checkout" : "Sign in to book"}
                        </button>
                      </div>
                    )}

                    {pendingPaymentBooking && (
                      <div className="sandbox-checkout">
                        <h3>3. Sandbox checkout</h3>
                        <p>
                      Booking #{pendingPaymentBooking.id} | Seat {pendingPaymentBooking.seat_number}
                        </p>
                        <p>
                          Amount: <strong>{formatPrice(selectedShowtime.ticket_price_paise)}</strong>
                        </p>
                        <p className="auth-description">
                          This is a simulated payment only. No real money is charged.
                          Complete the test within 10 minutes.
                        </p>
                        <div className="sandbox-actions">
                          <button
                            className="primary-button"
                            disabled={paymentBusy}
                            onClick={() => simulatePayment("success")}
                          >
                        {paymentBusy ? "Processing..." : "Simulate Successful Payment"}
                          </button>
                          <button
                            className="book-button"
                            disabled={paymentBusy}
                            onClick={() => simulatePayment("failure")}
                          >
                            Simulate Failed Payment
                          </button>
                        </div>
                      </div>
                    )}

                    {paymentResult && (
                      <div className="sandbox-payment-result">
                        <h3>
                          {paymentResult.status === "succeeded"
                            ? "Payment successful"
                            : "Payment failed"}
                        </h3>
                        <p>Payment reference: <strong>{paymentResult.reference}</strong></p>
                        <p>
                          Amount: {paymentResult.currency} {paymentResult.amount_rupees}
                        </p>
                        <p>Booking ID: {paymentResult.booking_id}</p>
                        <p>Status: {paymentResult.status}</p>
                      </div>
                    )}
                    {user?.role === "admin" && (
                      <p className="auth-description">Administrator accounts cannot book customer tickets.</p>
                    )}
                  </>
                )}
              </div>
            )}
          </section>
        )}

        <section className="experience-strip" id="experience">
          <div>
            <span className="strip-icon">*</span>
            <div><strong>Your night, your choice</strong><p>Browse movies and choose a showtime.</p></div>
          </div>
          <div>
            <span className="strip-icon">*</span>
            <div><strong>Pick your perfect seat</strong><p>Live availability from the booking API.</p></div>
          </div>
          <div>
            <span className="strip-icon">*</span>
            <div><strong>Booking made clear</strong><p>Review and manage your bookings.</p></div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <a className="brand footer-brand" href="/">
          <span className="brand-mark">C</span>
          <span>Cine<span>Book</span></span>
        </a>
        <p>Made for movie people. Built one feature at a time.</p>
        <span className="footer-status"><span className="live-dot" />DAY 4 | PAYMENT SANDBOX</span>
      </footer>
    </div>
  );
}

export default App;
