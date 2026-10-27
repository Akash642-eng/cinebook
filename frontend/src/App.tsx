/* eslint-disable react-hooks/set-state-in-effect -- Effects initiate API requests; their loading-state updates are intentional. */
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes, useNavigate, useParams } from "react-router-dom";
import "./App.css";

type Movie = { id:number; title:string; genre:string; language:string; duration_minutes:number; description:string; poster_url:string };
type User = { id:number; full_name:string; email:string; role:string; is_active:boolean };
type Showtime = { id:number; movie_id:number; movie_title:string; cinema_id:number; cinema_name:string; city:string; screen_id:number; screen_name:string; total_seats:number; starts_at:string; ticket_price_paise:number };
type Seat = { seat_number:number; status:"available"|"booked" };
type SeatAvailability = { showtime_id:number; total_seats:number; available_seats:number; booked_seats:number; seats:Seat[] };
type Booking = { id:number; user_id:number; showtime_id:number; seat_number:number; status:"pending_payment"|"confirmed"|"cancelled"; booked_at:string };
type Payment = { id:number; booking_id:number; amount_rupees:string; currency:string; provider:string; status:"succeeded"|"failed"; reference:string; created_at:string };
type Ticket = { id:number; booking_id:number; status:string; movie_title:string; showtime_id:number; starts_at:string; seat_number:number; created_at:string; verification_url:string; qr_url:string; pdf_url:string };
const TOKEN_KEY="cinebook_access_token";
async function api<T>(path:string, init:RequestInit={}, token?:string):Promise<T>{ const headers=new Headers(init.headers); if(init.body) headers.set("Content-Type","application/json"); if(token) headers.set("Authorization",`Bearer ${token}`); const r=await fetch(path,{...init,headers}); if(!r.ok){let msg=`Request failed (${r.status})`; try{const b=await r.json(); if(typeof b.detail==="string")msg=b.detail;}catch { /* Ignore non-JSON error bodies; retain the HTTP fallback message. */ } throw new Error(msg);} return r.json() as Promise<T>; }
const money=(p:number)=>new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(p/100);
const date=(v:string)=>new Intl.DateTimeFormat("en-IN",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Kolkata"}).format(new Date(v));
function Spinner({label="Loading CineBook"}:{label?:string}){return <div className="loading-state"><span className="spinner"/><span>{label}</span></div>}
function Shell(){
 const [movies,setMovies]=useState<Movie[]>([]),[moviesBusy,setMoviesBusy]=useState(true),[moviesError,setMoviesError]=useState("");
 const [token,setToken]=useState(()=>sessionStorage.getItem(TOKEN_KEY)||""),[user,setUser]=useState<User|null>(null),[authBusy,setAuthBusy]=useState(Boolean(sessionStorage.getItem(TOKEN_KEY)));
 const [query,setQuery]=useState(""),[genre,setGenre]=useState("All"); const navigate=useNavigate();
 const loadMovies=useCallback(async()=>{setMoviesBusy(true);setMoviesError("");try{setMovies(await api<Movie[]>("/api/movies"));}catch(e){setMoviesError(e instanceof Error?e.message:"Unable to load movies");}finally{setMoviesBusy(false);}},[]);
 useEffect(()=>{void loadMovies();},[loadMovies]);
 useEffect(()=>{let live=true;if(!token){setUser(null);setAuthBusy(false);return;}setAuthBusy(true);api<User>("/api/auth/me",{},token).then(v=>{if(live)setUser(v)}).catch(()=>{if(live){sessionStorage.removeItem(TOKEN_KEY);setToken("");setUser(null)}}).finally(()=>{if(live)setAuthBusy(false)});return()=>{live=false}},[token]);
 const signOut=()=>{sessionStorage.removeItem(TOKEN_KEY);setToken("");setUser(null);navigate("/");};
 const filtered=useMemo(()=>movies.filter(m=>(m.title+" "+m.genre+" "+m.language).toLowerCase().includes(query.toLowerCase())&&(genre==="All"||m.genre.toLowerCase()===genre.toLowerCase())),[movies,query,genre]);
 return <div className="app-shell"><header className="topbar"><Link className="brand" to="/"><span className="brand-icon">C</span><span>Cine<span className="brand-accent">Book</span><small>YOUR MOVIE, YOUR MOMENT</small></span></Link><nav className="main-nav"><NavLink to="/" end>Discover</NavLink>{user&&<NavLink to="/tickets">My tickets</NavLink>}{user?.role==="admin"&&<NavLink to="/admin">Studio</NavLink>}</nav><div className="top-actions">{authBusy?<span className="muted">CheckingÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦</span>:user?<><span className="user-greeting">Hi, {user.full_name.split(" ")[0]}</span><button className="button button-ghost button-small" onClick={signOut}>Sign out</button></>:<Link className="button button-primary button-small" to="/signin">Sign in <span>ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â€</span></Link>}</div></header>
 <Routes><Route path="/" element={<Home movies={filtered} allMovies={movies} busy={moviesBusy} error={moviesError} query={query} setQuery={setQuery} genre={genre} setGenre={setGenre} reload={loadMovies}/>}/><Route path="/movie/:movieId" element={<MovieRoute movies={movies} token={token} user={user} />}/><Route path="/signin" element={<AuthPage setToken={v=>{setToken(v);navigate("/")}}/>}/><Route path="/tickets" element={<TicketsPage token={token} user={user}/>}/><Route path="/admin" element={<AdminPage token={token} user={user}/>}/><Route path="*" element={<NotFound/>}/></Routes>
 <footer className="footer"><div className="footer-brand">Cine<span>Book</span></div><span>Made for the magic of the big screen.</span><span className="footer-links">Discover Ãƒâ€šÃ‚Â· Book Ãƒâ€šÃ‚Â· Experience</span></footer></div>
}
function Home({movies,allMovies,busy,error,query,setQuery,genre,setGenre,reload}:{movies:Movie[];allMovies:Movie[];busy:boolean;error:string;query:string;setQuery:(s:string)=>void;genre:string;setGenre:(s:string)=>void;reload:()=>void}){const genres=["All",...Array.from(new Set(allMovies.map(m=>m.genre).filter(Boolean)))];return <main><section className="hero"><div className="hero-copy"><div className="eyebrow"><span className="live-dot"/> THE CINEMA EXPERIENCE, REIMAGINED</div><h1>Some stories<br/>deserve the <em>big screen.</em></h1><p>Find the film that moves you. Choose your perfect seat. Make a night of it.</p><a href="#now-showing" className="button button-primary">Explore movies <span>ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬Å“</span></a><div className="hero-foot"><span>01 / DISCOVER</span><span>02 / RESERVE</span><span>03 / EXPERIENCE</span></div></div><div className="hero-art"><div className="hero-poster hero-poster-back"><span>THE ART OF</span><b>ESCAPE</b></div><div className="hero-poster hero-poster-front"><span>CINEMA IS</span><b>MAGIC.</b><small>ONLY ON THE BIG SCREEN</small></div><div className="hero-orbit"/><div className="hero-stamp">YOUR<br/>NEXT<br/>SCENE</div></div></section><section className="trust-row"><div><strong>Curated stories</strong><span>Find your next favourite</span></div><div><strong>Your perfect seat</strong><span>Choose where the magic happens</span></div><div><strong>Seamless booking</strong><span>From discovery to showtime</span></div></section>
 <section className="catalogue section-wrap" id="now-showing"><div className="section-title"><div><div className="eyebrow">HANDPICKED FOR YOU</div><h2>Now showing<span className="pink">.</span></h2><p>Big stories. Brilliant performances. Your next movie night.</p></div><span className="catalogue-count">{allMovies.length.toString().padStart(2,"0")} FILMS</span></div><div className="catalogue-tools"><label className="search-box"><span>ÃƒÂ¢Ã…â€™Ã¢â‚¬Â¢</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search films, genres, languages" aria-label="Search movies"/></label><div className="genre-filters">{genres.map(g=><button key={g} className={genre===g?"filter-chip active":"filter-chip"} onClick={()=>setGenre(g)}>{g}</button>)}</div></div>{busy?<div className="movie-grid">{Array.from({length:4},(_,i)=><div className="movie-skeleton" key={i}><div/><span/><span/></div>)}</div>:error?<div className="state-card"><h3>We couldn't load the films.</h3><p>{error}</p><button className="button button-primary" onClick={reload}>Try again</button></div>:movies.length===0?<div className="state-card"><h3>No films match your search.</h3><p>Try another title or clear your filters.</p><button className="button button-ghost" onClick={()=>{setQuery("");setGenre("All")}}>Clear filters</button></div>:<div className="movie-grid">{movies.map((m,i)=><article className="movie-card" key={m.id}><Link className="poster-link" to={`/movie/${m.id}`}><div className={`poster poster-${i%4}`}>{m.poster_url&&!m.poster_url.includes("placehold.co")?<img src={m.poster_url} alt={`${m.title} poster`} loading="lazy"/>:<div className="poster-placeholder"><span className="poster-index">CINEMA / {String(i+1).padStart(2,"0")}</span><strong>{m.title}</strong><small>{m.genre} Ãƒâ€šÃ‚Â· {m.language}</small></div>}<span className="poster-overlay">VIEW FILM ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â€</span></div></Link><div className="movie-meta"><div><span className="movie-genre">{m.genre||"FEATURE FILM"}</span><h3><Link to={`/movie/${m.id}`}>{m.title}</Link></h3><p>{m.language} <span>Ãƒâ€šÃ‚Â·</span> {m.duration_minutes} min</p></div><Link className="round-arrow" to={`/movie/${m.id}`} aria-label={`View ${m.title}`}>ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â€</Link></div></article>)}</div>}</section><section className="closing-banner"><div><div className="eyebrow">THE BEST NIGHTS ARE SHARED</div><h2>Make room for<br/><em>a little wonder.</em></h2></div><Link className="button button-light" to={movies[0]?`/movie/${movies[0].id}`:"/"}>Find your next film ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â€</Link></section></main>}
function MovieRoute({movies,token,user}:{movies:Movie[];token:string;user:User|null}){const {movieId}=useParams();const movie=movies.find(m=>m.id===Number(movieId));const [shows,setShows]=useState<Showtime[]>([]),[busy,setBusy]=useState(true),[error,setError]=useState("");useEffect(()=>{let live=true;setBusy(true);api<Showtime[]>(`/api/showtimes?movie_id=${movieId}`).then(v=>{if(live)setShows(v)}).catch(e=>{if(live)setError(e instanceof Error?e.message:"Could not load showtimes")}).finally(()=>{if(live)setBusy(false)});return()=>{live=false}},[movieId]);if(!movie)return <main className="section-wrap page-space"><Spinner label="Loading film detailsÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"/></main>;return <main className="section-wrap page-space"><Link className="back-link" to="/">ÃƒÂ¢Ã¢â‚¬ Ã‚Â Back to discovery</Link><div className="movie-detail"><div className="detail-poster">{movie.poster_url&&!movie.poster_url.includes("placehold.co")?<img src={movie.poster_url} alt={movie.title}/>:<div className="poster-placeholder"><span className="poster-index">CINEBOOK ORIGINAL SELECTION</span><strong>{movie.title}</strong><small>{movie.genre} Ãƒâ€šÃ‚Â· {movie.language}</small></div>}</div><div className="detail-copy"><div className="eyebrow">NOW SHOWING Ãƒâ€šÃ‚Â· FEATURE PRESENTATION</div><h1>{movie.title}</h1><div className="detail-tags"><span>{movie.genre}</span><span>{movie.language}</span><span>{movie.duration_minutes} minutes</span></div><p>{movie.description||"Discover this story on the big screen."}</p><h2>Choose your showtime</h2>{busy?<Spinner label="Finding showtimesÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"/>:error?<div className="state-card"><p>{error}</p></div>:shows.length===0?<div className="state-card"><p>No showtimes are currently listed for this film.</p></div>:<div className="showtime-list">{shows.map(s=><ShowtimeCard key={s.id} show={s} token={token} user={user}/>)}</div>}</div></div></main>}
/* CINEBOOK_RANDOM_OTP_UI_PATCH */ function ShowtimeCard({show,token,user}:{show:Showtime;token:string;user:User|null}){const [open,setOpen]=useState(false),[seats,setSeats]=useState<SeatAvailability|null>(null),[selected,setSelected]=useState<number|null>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState(""),[booking,setBooking]=useState<Booking|null>(null),[payment,setPayment]=useState<Payment|null>(null),[ticket,setTicket]=useState<Ticket|null>(null),[payMethod,setPayMethod]=useState<"card"|"upi">("card"),[cardName,setCardName]=useState(""),[cardNumber,setCardNumber]=useState(""),[upiId,setUpiId]=useState(""),[otpStep,setOtpStep]=useState(false),[demoOtp,setDemoOtp]=useState("");async function selectShow(){setOpen(v=>!v);setMessage("");if(!seats){setBusy(true);try{setSeats(await api<SeatAvailability>(`/api/showtimes/${show.id}/seats`))}catch(e){setMessage(e instanceof Error?e.message:"Could not load seats")}finally{setBusy(false)}}}async function reserve(){if(!token||!user){setMessage("Sign in before reserving a seat.");return}if(selected===null)return;setBusy(true);setMessage("");try{setBooking(await api<Booking>("/api/bookings",{method:"POST",body:JSON.stringify({showtime_id:show.id,seat_number:selected})},token));}catch(e){setMessage(e instanceof Error?e.message:"Could not reserve seat")}finally{setBusy(false)}}async function paySandbox(otp:string){if(!booking)return;setBusy(true);setMessage("");try{const instrument=payMethod==="card"?cardNumber.replace(/\D/g,"").slice(-4):upiId.trim().toLowerCase();const p=await api<Payment>("/api/payments/sandbox",{method:"POST",body:JSON.stringify({booking_id:booking.id,payment_method:payMethod,instrument,otp})},token);setPayment(p);if(p.status==="succeeded"){const ts=await api<Ticket[]>("/api/tickets/me",{},token);setTicket(ts.find(t=>t.booking_id===booking.id)||null);setMessage("Sandbox payment succeeded. Your ticket is ready below.")}else setMessage("Sandbox payment failed.")}catch(e){setMessage(e instanceof Error?e.message:"Sandbox payment failed")}finally{setBusy(false)}}return <article className="showtime-card"><div className="showtime-main"><div><strong>{date(show.starts_at)}</strong><span>{show.cinema_name} Ãƒâ€šÃ‚Â· {show.city}</span><small>{show.screen_name}</small></div><div className="showtime-price"><strong>{money(show.ticket_price_paise)}</strong><button className="button button-outline button-small" onClick={selectShow}>{open?"Close":"Choose seats"}</button></div></div>{open&&<div className="seat-flow">{busy&&!seats?<Spinner label="Loading seat mapÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"/>:seats&&<><div className="screen-arc"><span>SCREEN THIS WAY</span></div><div className="seat-grid">{seats.seats.map(s=><button key={s.seat_number} disabled={s.status!=="available"||Boolean(booking)} className={`seat ${s.status==="booked"?"seat-taken":""} ${selected===s.seat_number?"seat-picked":""}`} onClick={()=>setSelected(selected===s.seat_number?null:s.seat_number)} aria-label={`Seat ${s.seat_number} ${s.status}`}>{s.seat_number}</button>)}</div><div className="seat-legend"><span>ÃƒÂ¢Ã¢â‚¬â€Ã‚Â Available</span><span>ÃƒÂ¢Ã¢â‚¬â€Ã‚Â Selected</span><span>ÃƒÂ¢Ã¢â‚¬â€Ã‚Â Occupied</span></div>{!booking&&<button className="button button-primary full-width" disabled={selected===null||busy} onClick={reserve}>{busy?"Reserving seatÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦":selected===null?"Select a seat to continue":`Reserve seat ${selected} Ãƒâ€šÃ‚Â· ${money(show.ticket_price_paise)}`}</button>}</>}{booking&&!payment&&<div className="checkout-box premium-checkout"><div className="gateway-header"><div className="gateway-brand"><span className="gateway-brand-mark">C</span><span><strong>CineBook Pay</strong><small>SECURE DEMO CHECKOUT</small></span></div><span className="gateway-transaction">Booking #{booking.id}</span></div><div className="eyebrow">PAYMENT DETAILS</div><h3>{otpStep?"Verify your payment":"Review and pay"}</h3><p className="muted">Secure-looking portfolio simulation. No real payment is processed.</p><div className="payment-summary"><div><span>Showtime</span><strong>{date(show.starts_at)}</strong></div><div><span>Cinema</span><strong>{show.cinema_name}</strong></div><div><span>Seat</span><strong>{booking.seat_number}</strong></div><div><span>Booking</span><strong>#{booking.id}</strong></div><div className="payment-grand-total"><span>Total payable</span><strong>{money(show.ticket_price_paise)}</strong></div></div>{!otpStep&&<><div className="payment-methods"><button type="button" className={payMethod==="card"?"payment-method active":"payment-method"} onClick={()=>setPayMethod("card")}>Ã°Å¸â€™Â³ Card</button><button type="button" className={payMethod==="upi"?"payment-method active":"payment-method"} onClick={()=>setPayMethod("upi")}>Ã°Å¸â€œÂ± UPI</button></div>{payMethod==="card"?<div className="demo-payment-fields"><label>Name on card<input autoComplete="off" value={cardName} onChange={e=>setCardName(e.target.value)} placeholder="Demo cardholder" maxLength={80}/></label><label>Card number<input inputMode="numeric" autoComplete="off" value={cardNumber} onChange={e=>setCardNumber(e.target.value.replace(/\D/g,"").slice(0,16))} placeholder="4242 4242 4242 4242" maxLength={16}/></label><p className="muted small">Use test details only. Cards ending in 0000 simulate a decline; other valid demo numbers simulate approval. Never enter real card details.</p></div>:<div className="demo-payment-fields"><label>Demo UPI ID<input autoComplete="off" value={upiId} onChange={e=>setUpiId(e.target.value)} placeholder="demo@cinebook" maxLength={100}/></label><p className="muted small">Use a demo UPI ID. IDs containing Ã¢â‚¬Å“failÃ¢â‚¬Â simulate a decline; other valid IDs simulate approval. No UPI app or bank is contacted.</p></div>}<div className="gateway-note"><strong>Automatic payment decision</strong><span>The demo gateway validates your OTP and evaluates the test payment details. No success/failure selection.</span></div><button className="button button-primary full-width" disabled={busy||(payMethod==="card"?(cardName.trim().length<2||cardNumber.replace(/\s/g,"").length<12):!upiId.includes("@"))} onClick={async()=>{setDemoOtp("");setBusy(true);setMessage("");try{await api<{message:string}>("/api/payments/otp/request",{method:"POST",body:JSON.stringify({booking_id:booking.id})},token);setOtpStep(true);setMessage("Sandbox OTP generated. Check the backend logs for the code.")}catch(e){setMessage(e instanceof Error?e.message:"Could not generate OTP")}finally{setBusy(false)}}}>Continue to verification Ã¢â€ â€™</button></>}{otpStep&&<div className="demo-payment-fields"><p>Enter the six-digit demo OTP to continue.</p><label>Demo OTP<input inputMode="numeric" autoComplete="off" value={demoOtp} onChange={e=>setDemoOtp(e.target.value.replace(/\D/g,"").slice(0,6))} placeholder="6-digit OTP" maxLength={6}/></label><p className="muted small">A one-time code was generated for this sandbox booking. It expires in five minutes.</p><button className="button button-primary full-width" disabled={busy||demoOtp.length!==6} onClick={()=>paySandbox(demoOtp)}>{busy?"Processing demo paymentÃ¢â‚¬Â¦":"Verify OTP and pay"}</button><button type="button" className="button button-ghost full-width" disabled={busy} onClick={()=>setOtpStep(false)}>Back to payment details</button></div>}</div>}{payment&&<div className="checkout-box"><div className={payment.status==="succeeded"?"status-good":"status-bad"}>{payment.status==="succeeded"?"ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“ Payment successful":"Payment failed"}</div><h3>{payment.status==="succeeded"?"Your movie night is booked.":"We couldn't complete payment."}</h3><p>Booking #{payment.booking_id} Ãƒâ€šÃ‚Â· {payment.reference}</p>{ticket&&<div className="ticket-mini"><div><div className="eyebrow">YOUR DIGITAL TICKET</div><h3>{ticket.movie_title}</h3><p>{date(ticket.starts_at)} Ãƒâ€šÃ‚Â· Seat {ticket.seat_number}</p><p>Booking #{ticket.booking_id} Ãƒâ€šÃ‚Â· {ticket.status}</p></div><img src={ticket.qr_url} alt={`QR code for booking ${ticket.booking_id}`}/><a href={ticket.pdf_url} target="_blank" rel="noreferrer">Download printable PDF ticket</a><a href={ticket.verification_url} target="_blank" rel="noreferrer">Verify ticket ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â€</a><p className="muted small">For phone scanning, verification links must use a public HTTPS domain or a reachable LAN address. Localhost URLs work only on this computer.</p></div>}{payment.status==="succeeded"&&!ticket&&<p className="muted">Payment succeeded. Ticket is not available yet; open My tickets to refresh.</p>}</div>}{message&&<p className="inline-message" role="status">{message}</p>}</div>}</article>}
function AuthPage({setToken}:{setToken:(s:string)=>void}){const [mode,setMode]=useState<"login"|"register">("login"),[name,setName]=useState(""),[email,setEmail]=useState(""),[phone,setPhone]=useState(""),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState("");async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError("");setMessage("");try{if(mode==="register"){await api<User>("/api/auth/register",{method:"POST",body:JSON.stringify({full_name:name.trim(),email:email.trim().toLowerCase(),phone:phone.trim(),password})});setMode("login");setPassword("");setMessage("Account created. Sign in to continue.");}else{const r=await api<{access_token:string}>("/api/auth/login",{method:"POST",body:JSON.stringify({email:email.trim().toLowerCase(),password})});sessionStorage.setItem(TOKEN_KEY,r.access_token);setToken(r.access_token)}}catch(e){setError(e instanceof Error?e.message:"Authentication failed")}finally{setBusy(false)}}return <main className="auth-page"><div className="auth-aside"><div className="eyebrow">YOUR NEXT CHAPTER STARTS HERE</div><h1>Come for the film.<br/><em>Stay for the feeling.</em></h1><p>Your seat to unforgettable stories is just a sign-in away.</p><div className="auth-orbit">C<span>ÃƒÂ¢Ã…â€œÃ‚Â¦</span></div></div><section className="auth-card"><div className="eyebrow">CINEBOOK ACCOUNT</div><h2>{mode==="login"?"Welcome back.":"Join the experience."}</h2><p className="muted">{mode==="login"?"Sign in to pick up where your next movie night begins.":"Create your account and make every movie night count."}</p>{error&&<div className="alert alert-error">{error}</div>}{message&&<div className="alert alert-success">{message}</div>}<form onSubmit={submit} className="auth-form">{mode==="register"&&<label>Full name<input required minLength={2} maxLength={120} autoComplete="name" value={name} onChange={e=>setName(e.target.value)} placeholder="Your full name"/></label>}<label>Email address<input required type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/></label>{mode==="register"&&<label>Phone number<input required type="tel" minLength={7} maxLength={20} autoComplete="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+91 98765 43210"/></label>}<label>Password<input required type="password" minLength={mode==="register"?12:1} maxLength={128} autoComplete={mode==="login"?"current-password":"new-password"} value={password} onChange={e=>setPassword(e.target.value)} placeholder={mode==="register"?"At least 12 characters":"Your password"}/></label><button className="button button-primary full-width" disabled={busy}>{busy?<><span className="button-spinner"/> {mode==="login"?"Signing inÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦":"Creating accountÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"}</>:mode==="login"?"Sign in ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â„¢":"Create account ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â„¢"}</button></form><p className="auth-switch">{mode==="login"?"New to CineBook?":"Already have an account?"} <button onClick={()=>{setMode(mode==="login"?"register":"login");setError("");setMessage("")}}>{mode==="login"?"Create an account":"Sign in"}</button></p><Link className="back-link" to="/">ÃƒÂ¢Ã¢â‚¬ Ã‚Â Back to discovery</Link></section></main>}
function TicketsPage({token,user}:{token:string;user:User|null}){const [tickets,setTickets]=useState<Ticket[]>([]),[busy,setBusy]=useState(true),[error,setError]=useState("");const load=useCallback(()=>{if(!token){setBusy(false);return}setBusy(true);setError("");api<Ticket[]>("/api/tickets/me",{},token).then(setTickets).catch(e=>setError(e instanceof Error?e.message:"Could not load tickets")).finally(()=>setBusy(false))},[token]);useEffect(()=>{void load()},[load]);if(!user)return <main className="section-wrap page-space"><div className="state-card"><h2>Your tickets are waiting.</h2><p>Sign in to see your confirmed bookings and QR tickets.</p><Link className="button button-primary" to="/signin">Sign in</Link></div></main>;return <main className="section-wrap page-space"><div className="section-title"><div><div className="eyebrow">YOUR CINEBOOK ACCOUNT</div><h2>My tickets<span className="pink">.</span></h2><p>Your next great story, all in one place.</p></div><button className="button button-ghost" onClick={load}>ÃƒÂ¢Ã¢â‚¬ Ã‚Â» Refresh</button></div>{busy?<Spinner label="Retrieving your ticketsÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"/>:error?<div className="state-card"><p>{error}</p><button className="button button-primary" onClick={load}>Try again</button></div>:tickets.length===0?<div className="state-card"><h3>No tickets just yet.</h3><p>When your booking is confirmed, your ticket will appear here.</p><Link className="button button-primary" to="/">Explore films</Link></div>:<div className="tickets-list">{tickets.map(t=><article className="ticket-card" key={t.id}><div className="ticket-info"><div className="eyebrow">DIGITAL ADMISSION Ãƒâ€šÃ‚Â· #{t.booking_id}</div><h3>{t.movie_title}</h3><p>{date(t.starts_at)}</p><p>Seat {t.seat_number} Ãƒâ€šÃ‚Â· <span className="status-good">{t.status}</span></p><a href={t.verification_url} target="_blank" rel="noreferrer">Open ticket verification ÃƒÂ¢Ã¢â‚¬ Ã¢â‚¬â€</a></div><img src={t.qr_url} alt={`QR code for booking ${t.booking_id}`}/></article>)}</div>}</main>}
type AdminMovie = Movie & { is_active: boolean };

const emptyMovieForm = {
    title: "",
    genre: "",
    language: "English",
    duration_minutes: "120",
    description: "",
    poster_url: "",
};

type AdminAnalytics = {
    generated_at: string;
    admin_email: string;
    kpis: {
        total_users: number;
        total_movies: number;
        active_movies: number;
        total_cinemas: number;
        total_screens: number;
        upcoming_showtimes: number;
        total_bookings: number;
        confirmed_bookings: number;
        pending_bookings: number;
        cancelled_bookings: number;
        successful_payments: number;
        pending_payments: number;
        failed_payments: number;
        successful_payment_revenue_paise: number;
    };
    revenue_trend: { date: string; revenue_paise: number }[];
    booking_trend: { date: string; bookings: number }[];
    top_movies: {
        movie_id: number;
        title: string;
        confirmed_bookings: number;
    }[];
    recent_bookings: {
        booking_id: number;
        status: string;
        seat_number: string;
        booked_at: string;
        customer_name: string;
        customer_email: string;
        movie_title: string;
        cinema_name: string;
        showtime: string;
        payment_amount_paise: number | null;
        payment_status: string | null;
    }[];
    upcoming_shows: {
        showtime_id: number;
        movie_title: string;
        cinema_name: string;
        city: string;
        screen_name: string;
        starts_at: string;
        ticket_price_paise: number;
        total_seats: number;
    }[];
};
function AdminPage({ token, user }: { token: string; user: User | null }) {
    const [data, setData] = useState<{
        admin_email: string;
        statistics: { total_users: number; total_movies: number };
    } | null>(null);
    const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
    const [movies, setMovies] = useState<AdminMovie[]>([]);
    const [busy, setBusy] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [editingId, setEditingId] = useState<number | null>(null);
    const [form, setForm] = useState(emptyMovieForm);
    const [showForm, setShowForm] = useState(false);

    const loadDashboard = useCallback(async () => {
        const result = await api<{
            admin_email: string;
            statistics: { total_users: number; total_movies: number };
        }>("/api/admin/dashboard", {}, token);
        setData(result);
    }, [token]);

    const loadAnalytics = useCallback(async () => {
        const result = await api<AdminAnalytics>("/api/admin/analytics", {}, token);
        setAnalytics(result);
    }, [token]);

    const loadMovies = useCallback(async () => {
        const result = await api<AdminMovie[]>("/api/admin/movies", {}, token);
        setMovies(result);
    }, [token]);

    useEffect(() => {
        let live = true;

        if (!token || user?.role !== "admin") {
            setBusy(false);
            return () => { live = false; };
        }

        setBusy(true);
        setError("");

        Promise.all([loadDashboard(), loadMovies(), loadAnalytics()])
            .catch((e: unknown) => {
                if (live) {
                    setError(e instanceof Error ? e.message : "Unable to load studio data");
                }
            })
            .finally(() => {
                if (live) setBusy(false);
            });

        return () => { live = false; };
    }, [token, user, loadDashboard, loadMovies, loadAnalytics]);

    function startCreate() {
        setEditingId(null);
        setForm(emptyMovieForm);
        setError("");
        setNotice("");
        setShowForm(true);
    }

    function startEdit(movie: AdminMovie) {
        setEditingId(movie.id);
        setForm({
            title: movie.title,
            genre: movie.genre,
            language: movie.language,
            duration_minutes: String(movie.duration_minutes),
            description: movie.description,
            poster_url: movie.poster_url,
        });
        setError("");
        setNotice("");
        setShowForm(true);
    }

    async function submitMovie(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSaving(true);
        setError("");
        setNotice("");

        const payload = {
            title: form.title.trim(),
            genre: form.genre.trim(),
            language: form.language.trim(),
            duration_minutes: Number(form.duration_minutes),
            description: form.description.trim(),
            poster_url: form.poster_url.trim(),
        };

        try {
            if (editingId === null) {
                await api<AdminMovie>("/api/admin/movies", {
                    method: "POST",
                    body: JSON.stringify({ ...payload, is_active: true }),
                }, token);
                setNotice("Movie added to the catalogue.");
            } else {
                await api<AdminMovie>(`/api/admin/movies/${editingId}`, {
                    method: "PATCH",
                    body: JSON.stringify(payload),
                }, token);
                setNotice("Movie details updated.");
            }

            setShowForm(false);
            setEditingId(null);
            setForm(emptyMovieForm);
            await Promise.all([loadMovies(), loadDashboard()]);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Unable to save movie");
        } finally {
            setSaving(false);
        }
    }

    async function toggleMovie(movie: AdminMovie) {
        setError("");
        setNotice("");

        try {
            await api<AdminMovie>(`/api/admin/movies/${movie.id}/status`, {
                method: "PATCH",
                body: JSON.stringify({ is_active: !movie.is_active }),
            }, token);

            setNotice(
                movie.is_active
                    ? `${movie.title} has been deactivated.`
                    : `${movie.title} is now active.`,
            );
            await Promise.all([loadMovies(), loadDashboard()]);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Unable to change movie status");
        }
    }

    if (user?.role !== "admin") {
        return (
            <main className="section-wrap page-space">
                <div className="state-card">
                    <h2>Restricted area</h2>
                    <p>This studio dashboard is available to administrator accounts.</p>
                    <Link to="/" className="button button-primary">Return home</Link>
                </div>
            </main>
        );
    }

    return (
        <main className="section-wrap page-space admin-console">
            <div className="admin-heading">
                <div>
                    <div className="eyebrow">CINEBOOK OPERATIONS</div>
                    <h2>Studio overview<span className="pink">.</span></h2>
                    <p className="muted">Manage the film catalogue and its public availability.</p>
                </div>
                <button className="button button-primary" onClick={startCreate}>
                    + Add movie
                </button>
            </div>

            {error && <div className="alert alert-error" role="alert">{error}</div>}
            {notice && <div className="alert alert-success" role="status">{notice}</div>}

            {busy ? <Spinner label="Loading studio catalogue..." /> : (
                <>
                    {data && (
                        <div className="stats-grid">
                            <div className="stat-card">
                                <span>Registered customers</span>
                                <strong>{data.statistics.total_users}</strong>
                            </div>
                            <div className="stat-card">
                                <span>Active catalogue</span>
                                <strong>{data.statistics.total_movies}</strong>
                            </div>
                            <div className="stat-card">
                                <span>Administrator</span>
                                <strong className="stat-email">{data.admin_email}</strong>
                            </div>
                        </div>
                    )}

                    {analytics && (
                        <section className="command-center-dashboard" aria-label="Command Center analytics">
                            <div className="command-center-section-heading">
                                <div>
                                    <div className="eyebrow">LIVE PLATFORM METRICS</div>
                                    <h3>Command Center</h3>
                                    <p className="muted">Operational overview from CineBook data.</p>
                                </div>
                                <span className="command-center-live"><span /> Analytics loaded</span>
                            </div>

                            <div className="command-center-kpis">
                                <article className="command-center-kpi">
                                    <span>Total bookings</span>
                                    <strong>{analytics.kpis.total_bookings.toLocaleString("en-IN")}</strong>
                                    <small>{analytics.kpis.confirmed_bookings} confirmed</small>
                                </article>
                                <article className="command-center-kpi">
                                    <span>Successful revenue</span>
                                    <strong>{money(analytics.kpis.successful_payment_revenue_paise)}</strong>
                                    <small>{analytics.kpis.successful_payments} successful payments</small>
                                </article>
                                <article className="command-center-kpi">
                                    <span>Registered customers</span>
                                    <strong>{analytics.kpis.total_users.toLocaleString("en-IN")}</strong>
                                    <small>Platform accounts</small>
                                </article>
                                <article className="command-center-kpi">
                                    <span>Active movies</span>
                                    <strong>{analytics.kpis.active_movies}</strong>
                                    <small>{analytics.kpis.total_movies} movies in catalogue</small>
                                </article>
                                <article className="command-center-kpi">
                                    <span>Cinemas & screens</span>
                                    <strong>{analytics.kpis.total_cinemas} <span className="command-center-inline-unit">/ {analytics.kpis.total_screens}</span></strong>
                                    <small>Cinemas / screens</small>
                                </article>
                                <article className="command-center-kpi">
                                    <span>Upcoming shows</span>
                                    <strong>{analytics.kpis.upcoming_showtimes}</strong>
                                    <small>{analytics.kpis.pending_bookings} pending bookings</small>
                                </article>
                            </div>

                            <div className="command-center-panels">
                                <section className="command-center-panel">
                                    <div className="command-center-panel-heading">
                                        <div>
                                            <div className="eyebrow">PAYMENT PERFORMANCE</div>
                                            <h4>Revenue trend</h4>
                                        </div>
                                        <span className="command-center-panel-meta">INR</span>
                                    </div>
                                    {analytics.revenue_trend.length === 0 ? (
                                        <p className="muted">No revenue trend data available.</p>
                                    ) : (
                                        <div className="command-center-chart">
                                            {analytics.revenue_trend.map((point) => {
                                                const maximum = Math.max(
                                                    1,
                                                    ...analytics.revenue_trend.map((item) => item.revenue_paise),
                                                );
                                                const height = point.revenue_paise > 0
                                                    ? Math.max(6, (point.revenue_paise / maximum) * 100)
                                                    : 3;
                                                return (
                                                    <div className="command-center-bar-column" key={point.date}>
                                                        <span className="command-center-bar-value">{money(point.revenue_paise)}</span>
                                                        <div className="command-center-bar-track">
                                                            <div
                                                                className="command-center-bar"
                                                                style={{ height: `${height}%` }}
                                                                title={`${point.date}: ${money(point.revenue_paise)}`}
                                                            />
                                                        </div>
                                                        <span className="command-center-bar-label">
                                                            {new Date(`${point.date}T00:00:00`).toLocaleDateString("en-IN", {
                                                                day: "2-digit",
                                                                month: "short",
                                                                timeZone: "Asia/Kolkata",
                                                            })}
                                                        </span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </section>

                                <section className="command-center-panel">
                                    <div className="command-center-panel-heading">
                                        <div>
                                            <div className="eyebrow">AUDIENCE FAVOURITES</div>
                                            <h4>Top movies</h4>
                                        </div>
                                        <span className="command-center-panel-meta">CONFIRMED</span>
                                    </div>
                                    {analytics.top_movies.length === 0 ? (
                                        <p className="muted">No confirmed movie bookings yet.</p>
                                    ) : (
                                        <div className="command-center-top-movies">
                                            {analytics.top_movies.map((movie, index) => {
                                                const maximum = Math.max(
                                                    1,
                                                    ...analytics.top_movies.map((item) => item.confirmed_bookings),
                                                );
                                                return (
                                                    <div className="command-center-movie-row" key={movie.movie_id}>
                                                        <span className="command-center-rank">{String(index + 1).padStart(2, "0")}</span>
                                                        <div className="command-center-movie-info">
                                                            <div className="command-center-movie-label">
                                                                <strong>{movie.title}</strong>
                                                                <span>{movie.confirmed_bookings}</span>
                                                            </div>
                                                            <div className="command-center-progress-track">
                                                                <div
                                                                    className="command-center-progress"
                                                                    style={{ width: `${(movie.confirmed_bookings / maximum) * 100}%` }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </section>
                            </div>

                            <div className="command-center-panels">
                                <section className="command-center-panel">
                                    <div className="command-center-panel-heading">
                                        <div>
                                            <div className="eyebrow">LATEST ACTIVITY</div>
                                            <h4>Recent bookings</h4>
                                        </div>
                                        <span className="command-center-panel-meta">{analytics.recent_bookings.length} records</span>
                                    </div>
                                    {analytics.recent_bookings.length === 0 ? (
                                        <p className="muted">No bookings to display.</p>
                                    ) : (
                                        <div className="command-center-table-wrap">
                                            <table className="command-center-table">
                                                <thead>
                                                    <tr>
                                                        <th>Booking</th>
                                                        <th>Customer / movie</th>
                                                        <th>Status</th>
                                                        <th>Payment</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {analytics.recent_bookings.map((booking) => (
                                                        <tr key={booking.booking_id}>
                                                            <td>
                                                                <strong>#{booking.booking_id}</strong>
                                                                <small>{booking.seat_number ? `Seat ${booking.seat_number}` : "Seat —"}</small>
                                                            </td>
                                                            <td>
                                                                <strong>{booking.customer_name || "Customer"}</strong>
                                                                <small>{booking.movie_title}</small>
                                                            </td>
                                                            <td>
                                                                <span className={`command-center-status status-${booking.status.replace(/[^a-z0-9_-]/gi, "").toLowerCase()}`}>
                                                                    {booking.status.replace(/_/g, " ")}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <strong>{booking.payment_amount_paise == null ? "—" : money(booking.payment_amount_paise)}</strong>
                                                                <small>{booking.payment_status || "No payment"}</small>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </section>

                                <section className="command-center-panel">
                                    <div className="command-center-panel-heading">
                                        <div>
                                            <div className="eyebrow">SCHEDULE</div>
                                            <h4>Upcoming shows</h4>
                                        </div>
                                        <span className="command-center-panel-meta">{analytics.upcoming_shows.length} listed</span>
                                    </div>
                                    {analytics.upcoming_shows.length === 0 ? (
                                        <p className="muted">No upcoming shows are scheduled.</p>
                                    ) : (
                                        <div className="command-center-upcoming">
                                            {analytics.upcoming_shows.map((show) => (
                                                <article className="command-center-show" key={show.showtime_id}>
                                                    <div className="command-center-show-date">
                                                        <strong>{new Date(show.starts_at).toLocaleDateString("en-IN", {
                                                            day: "2-digit",
                                                            timeZone: "Asia/Kolkata",
                                                        })}</strong>
                                                        <small>{new Date(show.starts_at).toLocaleDateString("en-IN", {
                                                            month: "short",
                                                            timeZone: "Asia/Kolkata",
                                                        })}</small>
                                                    </div>
                                                    <div className="command-center-show-info">
                                                        <strong>{show.movie_title}</strong>
                                                        <span>{show.cinema_name} · {show.screen_name}</span>
                                                        <small>{date(show.starts_at)}</small>
                                                    </div>
                                                    <div className="command-center-show-price">
                                                        <strong>{money(show.ticket_price_paise)}</strong>
                                                        <small>{show.total_seats} seats</small>
                                                    </div>
                                                </article>
                                            ))}
                                        </div>
                                    )}
                                </section>
                            </div>
                        </section>
                    )}
                    {showForm && (
                        <section className="admin-form-panel">
                            <div className="admin-panel-heading">
                                <div>
                                    <div className="eyebrow">FILM DETAILS</div>
                                    <h3>{editingId === null ? "Add a movie" : "Edit movie"}</h3>
                                </div>
                                <button
                                    type="button"
                                    className="button button-ghost button-small"
                                    onClick={() => setShowForm(false)}
                                    disabled={saving}
                                >
                                    Cancel
                                </button>
                            </div>

                            <form className="admin-movie-form" onSubmit={submitMovie}>
                                <label>
                                    Movie title
                                    <input required maxLength={150} value={form.title}
                                        onChange={e => setForm({ ...form, title: e.target.value })}
                                        placeholder="Enter movie title" />
                                </label>
                                <label>
                                    Genre
                                    <input required maxLength={100} value={form.genre}
                                        onChange={e => setForm({ ...form, genre: e.target.value })}
                                        placeholder="Drama, Thriller, Comedy..." />
                                </label>
                                <label>
                                    Language
                                    <input required maxLength={50} value={form.language}
                                        onChange={e => setForm({ ...form, language: e.target.value })}
                                        placeholder="English, Kannada..." />
                                </label>
                                <label>
                                    Duration (minutes)
                                    <input required type="number" min={1} max={600}
                                        value={form.duration_minutes}
                                        onChange={e => setForm({ ...form, duration_minutes: e.target.value })} />
                                </label>
                                <label className="admin-form-wide">
                                    Poster image URL
                                    <input required type="url" maxLength={500} value={form.poster_url}
                                        onChange={e => setForm({ ...form, poster_url: e.target.value })}
                                        placeholder="https://example.com/poster.jpg" />
                                </label>
                                <label className="admin-form-wide">
                                    Description
                                    <textarea required maxLength={10000} rows={4} value={form.description}
                                        onChange={e => setForm({ ...form, description: e.target.value })}
                                        placeholder="Describe the film..." />
                                </label>
                                <div className="admin-form-wide admin-form-actions">
                                    <button className="button button-primary" disabled={saving}>
                                        {saving ? "Saving..." : editingId === null ? "Create movie" : "Save changes"}
                                    </button>
                                    <button type="button" className="button button-ghost"
                                        disabled={saving} onClick={() => setShowForm(false)}>
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </section>
                    )}

                    <section className="admin-catalogue">
                        <div className="admin-panel-heading">
                            <div>
                                <div className="eyebrow">CATALOGUE MANAGEMENT</div>
                                <h3>All movies <span className="catalogue-count">({movies.length})</span></h3>
                            </div>
                            <button type="button" className="button button-ghost button-small"
                                onClick={() => {
                                    setBusy(true);
                                    Promise.all([loadMovies(), loadDashboard()])
                                        .catch(e => setError(e instanceof Error ? e.message : "Refresh failed"))
                                        .finally(() => setBusy(false));
                                }}>
                                Refresh
                            </button>
                        </div>

                        {movies.length === 0 ? (
                            <div className="state-card">
                                <h3>No movies in the catalogue yet.</h3>
                                <p>Add your first movie to make it available for the CineBook experience.</p>
                            </div>
                        ) : (
                            <div className="admin-movie-list">
                                {movies.map(movie => (
                                    <article className="admin-movie-row" key={movie.id}>
                                        <div className="admin-movie-art">
                                            <img src={movie.poster_url} alt="" loading="lazy"
                                                onError={e => { e.currentTarget.style.visibility = "hidden"; }} />
                                        </div>
                                        <div className="admin-movie-info">
                                            <div className="admin-movie-title">
                                                <h4>{movie.title}</h4>
                                                <span className={movie.is_active ? "admin-status active" : "admin-status inactive"}>
                                                    {movie.is_active ? "Active" : "Inactive"}
                                                </span>
                                            </div>
                                            <p>{movie.genre} Â· {movie.language} Â· {movie.duration_minutes} min</p>
                                            <p className="admin-movie-description">{movie.description}</p>
                                        </div>
                                        <div className="admin-movie-actions">
                                            <button type="button" className="button button-ghost button-small"
                                                onClick={() => startEdit(movie)}>
                                                Edit
                                            </button>
                                            <button type="button"
                                                className={movie.is_active ? "button button-ghost button-small" : "button button-primary button-small"}
                                                onClick={() => void toggleMovie(movie)}>
                                                {movie.is_active ? "Deactivate" : "Activate"}
                                            </button>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        )}
                    </section>
                </>
            )}
        </main>
    );
}
function NotFound(){return <main className="section-wrap page-space"><div className="state-card"><div className="eyebrow">404 Ãƒâ€šÃ‚Â· LOST IN THE LOBBY</div><h2>This scene isn't in the script.</h2><p>The page may have moved. Let's get you back to the films.</p><Link className="button button-primary" to="/">Back to CineBook</Link></div></main>}
export default function App(){return <BrowserRouter><Shell/></BrowserRouter>}
